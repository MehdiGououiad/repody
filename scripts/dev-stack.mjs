#!/usr/bin/env node
/**
 * Start backend Docker stack, then production Next.js on the host (Option A).
 * Streams all platform logs (Docker + web) into this terminal.
 * Ctrl+C stops Next.js, log tail, and runs `docker compose down`.
 *
 * Usage:
 *   pnpm dev:nowarmup   — fast boot (no Repody VLM warmup)
 *   pnpm dev:warmup                — pull Repody VLM + warm before Next.js
 *   pnpm dev:warmup -- --logs      — Grafana/Loki/Promtail
 *   pnpm dev:warmup -- --traces    — logs + Tempo + OTEL
 *   pnpm dev:warmup -- --glitchtip — GlitchTip error tracking
 *   pnpm dev:warmup -- --logs --glitchtip
 *   pnpm dev:nowarmup -- --rebuild — force a fresh `next build`
 *
 * For hot-reload UI development: pnpm dev:ui (requires backend already running).
 */
import { spawn, spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { join } from "node:path";
import { spawnPrefixed } from "./log-prefix.mjs";

const mode = process.argv[2] === "warmup" ? "warmup" : "nowarmup";
const forceRebuild = process.argv.includes("--rebuild");
const withTraces = process.argv.includes("--traces");
const withLogs = process.argv.includes("--logs") || withTraces;
const withGlitchtip = process.argv.includes("--glitchtip");
const infraCmd = mode === "warmup" ? "infra:warmup" : "infra";
const servicesCmd = mode === "warmup" ? "services:warmup" : "services";
const obsUpCmd = mode === "warmup" ? "obs:up:warmup" : "obs:up";
const downCmd = mode === "warmup" ? "down:warmup" : "down";
const logsCmd = mode === "warmup" ? "logs:platform:warmup" : "logs:platform";
const buildIdPath = join(process.cwd(), ".next", "BUILD_ID");
const standaloneServerPath = join(
  process.cwd(),
  ".next",
  "standalone",
  "server.js"
);

/** @type {import("node:child_process").ChildProcess | null} */
let webProcess = null;
/** @type {import("node:child_process").ChildProcess | null} */
let logsProcess = null;
let stackStarted = false;
let shuttingDown = false;

const childEnv = {
  ...process.env,
  DOCKER_BUILDKIT: "1",
  COMPOSE_DOCKER_CLI_BUILD: "1",
  BACKEND_URL: process.env.BACKEND_URL ?? "http://127.0.0.1:8000",
  AUDIT_WARM_MODELS: process.env.AUDIT_WARM_MODELS ?? "repody-vlm",
  AUDIT_COMPOSE_STACK:
    process.env.AUDIT_COMPOSE_STACK ??
    (process.argv[2] === "warmup" ? "dev-warmup" : "dev"),
  AUDIT_DEV_OBS: withTraces ? "traces" : withLogs ? "logs" : "none",
};

function runSync(label, command, args) {
  console.error(`\n▶ ${label}\n`);
  const result = spawnSync(command, args, {
    stdio: "inherit",
    shell: process.platform === "win32",
    env: childEnv,
  });
  if (result.status !== 0) {
    process.exit(result.status ?? 1);
  }
}

function killProcessTree(pid) {
  if (!pid) return;
  if (process.platform === "win32") {
    spawnSync("taskkill", ["/T", "/F", "/PID", String(pid)], {
      shell: true,
      stdio: "ignore",
    });
    return;
  }
  try {
    process.kill(-pid, "SIGTERM");
  } catch {
    try {
      process.kill(pid, "SIGTERM");
    } catch {
      // already exited
    }
  }
}

function stopChild(proc) {
  if (!proc || proc.killed || proc.exitCode != null) return;
  killProcessTree(proc.pid);
}

function stopWeb() {
  stopChild(webProcess);
  webProcess = null;
}

function stopLogs() {
  stopChild(logsProcess);
  logsProcess = null;
}

function stopDocker() {
  if (!stackStarted) return;
  console.error("\n▶ Stopping Docker stack…\n");
  spawnSync("node", ["scripts/docker.mjs", downCmd], {
    stdio: "inherit",
    shell: process.platform === "win32",
    env: { ...childEnv, AUDIT_DEV_OBS: "traces" },
  });
  stackStarted = false;
}

function shutdown(reason) {
  if (shuttingDown) return;
  shuttingDown = true;
  console.error(`\n▶ Shutting down platform (${reason})…`);
  stopWeb();
  stopLogs();
  stopDocker();
  process.exit(0);
}

process.on("SIGINT", () => shutdown("Ctrl+C"));
process.on("SIGTERM", () => shutdown("SIGTERM"));

if (withGlitchtip) {
  runSync("Starting error tracking (GlitchTip)", "node", [
    "scripts/platform.mjs",
    "up",
    "--modules-only",
    "--with=errors",
    "--detach",
  ]);
}

if (withLogs) {
  const obsLabel = withTraces
    ? "Starting observability (Grafana/Loki + Tempo/OTEL)"
    : "Starting observability (Grafana/Loki — no traces)";
  runSync(obsLabel, "node", ["scripts/docker.mjs", obsUpCmd]);
}

runSync("Starting infra (postgres, redis, minio, hatchet)", "node", [
  "scripts/docker.mjs",
  infraCmd,
]);

stackStarted = true;

if (mode === "warmup") {
  runSync("Preparing Repody VLM in Docker Model Runner", "node", [
    "scripts/prepare-repody-vlm-model.mjs",
  ]);
}

runSync(
  mode === "warmup"
    ? "Starting backend with Repody VLM warmup enabled"
    : "Starting backend without warmup (fast boot)",
  "node",
  ["scripts/docker.mjs", servicesCmd]
);

runSync("Waiting for API health", "node", ["scripts/wait-for-api.mjs"]);

if (mode === "warmup") {
  runSync("Waiting for Repody VLM warmup", "node", ["scripts/wait-for-warmup.mjs"]);
}

if (forceRebuild || !existsSync(buildIdPath)) {
  runSync("Building Next.js (production)", "pnpm", ["build"]);
} else {
  console.error(
    "\n▶ Using existing production build (.next). Run with --rebuild to rebuild.\n"
  );
}

runSync("Preparing standalone server", "node", [
  "scripts/prepare-standalone.mjs",
]);

const obsLines = withLogs
  ? withTraces
    ? ` Grafana   : http://localhost:3001  (admin / audit) — logs + traces
 Tempo     : OTLP http://localhost:4318/v1/traces`
    : ` Grafana   : http://localhost:3001  (admin / audit) — logs only`
  : "";
const glitchtipLine = withGlitchtip
  ? ` GlitchTip : http://localhost:8090  (errors + API warnings)`
  : "";

console.error(`
══════════════════════════════════════════════════════════════════════
 Platform live — streaming logs (source of truth)
──────────────────────────────────────────────────────────────────────
 Docker : api, worker, worker-fast, postgres, redis, minio,
          hatchet-lite, hatchet-postgres (last 300 lines + follow)
 Web    : http://localhost:3000  (prefixed [web])
 API    : http://localhost:8000
${glitchtipLine ? `${glitchtipLine}\n` : ""}${obsLines ? `${obsLines}\n` : ""} Ctrl+C : stop web + logs + docker compose down
══════════════════════════════════════════════════════════════════════
`);

logsProcess = spawn("node", ["scripts/docker.mjs", logsCmd], {
  stdio: "inherit",
  shell: process.platform === "win32",
  env: childEnv,
  cwd: process.cwd(),
});

logsProcess.on("exit", () => {
  logsProcess = null;
  if (!shuttingDown) shutdown("docker logs exited");
});

logsProcess.on("error", (err) => {
  console.error("[docker-logs]", err);
});

webProcess = spawnPrefixed("web", process.execPath, [standaloneServerPath], {
  env: { ...childEnv, PORT: childEnv.PORT ?? "3000" },
  cwd: join(process.cwd(), ".next", "standalone"),
});

webProcess.on("exit", (code, signal) => {
  if (shuttingDown) return;
  if (signal) {
    shutdown(signal);
    return;
  }
  shutdown(`web exited (${code ?? 0})`);
});

webProcess.on("error", (err) => {
  console.error("[web]", err);
  shutdown("web process error");
});
