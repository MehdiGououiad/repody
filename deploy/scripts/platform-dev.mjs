#!/usr/bin/env node
/**
 * Repody local platform CLI (Windows + macOS + Linux) - same Hub images everywhere.
 *
 *   pnpm platform setup     # once
 *   pnpm platform           # pull images + start stack + host NuExtract
 *   pnpm platform status | stop | doctor | logs | help
 *
 * Images: mehdigououiad/repody-backend + repody-web (linux/amd64 + linux/arm64)
 * Overlay: compose.yaml + compose.portable.yaml
 */
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import {
  BACKEND_ENV,
  busyPorts,
  composeArgs as composeArgsFor,
  copyIfMissing,
  fetchProbe,
  findExecutable,
  llamaServe,
  parseEnvFile,
  ROOT,
  run,
  setEnvKeys,
} from "./runtime-env.mjs";

const AUTH_ENV = path.join(ROOT, ".env.local");
const COMPOSE_ENV_EXAMPLE = path.join(ROOT, "deploy/env/compose.env.example");
const AUTH_ENV_EXAMPLE = path.join(ROOT, "deploy/env.auth.example");
const LLAMA_PATHS = path.join(ROOT, "deploy/llamacpp/paths.local.env");
const LLAMA_MAC_EXAMPLE = path.join(ROOT, "deploy/llamacpp/paths.mac.env.example");
const LLAMA_EXAMPLE = path.join(ROOT, "deploy/llamacpp/paths.local.env.example");
const BACKEND_IMAGE = process.env.REPODY_BACKEND_IMAGE || "mehdigououiad/repody-backend:0.1.0";
const WEB_IMAGE = process.env.REPODY_WEB_IMAGE || "mehdigououiad/repody-web:0.1.0";

const rawArgs = process.argv.slice(2);
const flags = new Set(rawArgs.filter((a) => a.startsWith("-")));
const command =
  rawArgs.find((a) => !a.startsWith("-")) ||
  (flags.has("--help") || flags.has("-h") ? "help" : "up");
const isDarwin = process.platform === "darwin";
const isWin = process.platform === "win32";

const opts = {
  platformOnly: flags.has("--platform-only"),
  withNuextract: !(
    flags.has("--no-nuextract") ||
    flags.has("--no-vlm") ||
    flags.has("--platform-only")
  ),
  // Observability (Grafana/Loki/Tempo/Bugsink) on by default for Hub platform.
  withObs: !(flags.has("--no-obs") || flags.has("--no-observability")),
  skipPull: flags.has("--no-pull"),
};

function printHelp() {
  console.log(`
Repody platform CLI (same on Windows, macOS, Linux)

Flow (new PC):
  1) pnpm install && pnpm doctor
  2) Download NuExtract GGUFs → set deploy/llamacpp/paths.local.env
  3) pnpm platform setup     # once — env files + pull Hub images
  4) pnpm platform           # start platform + host NuExtract
  5) pnpm platform status    # health
  6) pnpm platform stop      # tear down

Commands:
  up         Start Hub platform + host NuExtract   [default]
  setup      Once: env / paths + pull Hub images
  bootstrap  setup + up (new machine after git clone / pnpm install)
  doctor     Check everything needed before start (Node, Docker, llama-server, GGUFs, env)
  status     Probe services + observability URLs
  logs       Tail API/web/worker Docker logs
  stop       Stop host NuExtract + Compose
  help       This help

Options (pnpm platform -- … / pnpm platform setup -- …):
  --no-nuextract     Skip host NuExtract (:8081)
  --no-obs           Skip Grafana/Loki/Tempo/Bugsink (on by default)
  --platform-only    Containers only (no host model)
  --no-pull          Do not docker pull (setup + up)

Images: ${BACKEND_IMAGE} · ${WEB_IMAGE}
Guide: docs/LOCAL.md
`);
}

function composeArgs(...parts) {
  return composeArgsFor(["compose.yaml", "compose.portable.yaml"], ...parts);
}

function llamaInstallHint() {
  if (isDarwin) return "brew install llama.cpp";
  if (isWin) return "winget install ggml.llamacpp   (or put llama-server on PATH)";
  return "install llama.cpp so llama-server is on PATH";
}

function copyEnvFiles() {
  copyIfMissing(COMPOSE_ENV_EXAMPLE, BACKEND_ENV);
  copyIfMissing(AUTH_ENV_EXAMPLE, AUTH_ENV);
  const llamaSrc = isDarwin && fs.existsSync(LLAMA_MAC_EXAMPLE) ? LLAMA_MAC_EXAMPLE : LLAMA_EXAMPLE;
  copyIfMissing(llamaSrc, LLAMA_PATHS);
}

/** Point backend/.env at the host model and toggle OTEL for this run (setup / up only). */
function patchBackendEnv() {
  const llamaEnv = parseEnvFile(LLAMA_PATHS);
  setEnvKeys(BACKEND_ENV, {
    AUDIT_LLAMACPP_BASE_URL: "http://127.0.0.1:8081/v1",
    AUDIT_LLAMACPP_SERVED_MODEL:
      (llamaEnv.LLAMACPP_MODEL_ALIAS || "").trim() ||
      process.env.AUDIT_LLAMACPP_SERVED_MODEL ||
      "nuextract3-q4_k_m",
    AUDIT_OTEL_ENABLED: opts.withObs ? "true" : "false",
    ...(opts.withObs && {
      AUDIT_OTEL_EXPORTER_ENDPOINT: "http://otel-collector:4318/v1/traces",
      AUDIT_OTEL_SERVICE_NAME: "repody-api",
      AUDIT_LOG_JSON: "true",
    }),
  });
}

function nuextractConfigured() {
  const env = parseEnvFile(LLAMA_PATHS);
  const model = (env.LLAMACPP_MODEL || "").trim();
  const mmproj = (env.LLAMACPP_MMPROJ || "").trim();
  if (!model || !fs.existsSync(model)) {
    return {
      ok: false,
      reason: "Set LLAMACPP_MODEL in deploy/llamacpp/paths.local.env to a NuExtract3 .gguf path",
    };
  }
  if (!mmproj || !fs.existsSync(mmproj)) {
    return {
      ok: false,
      reason: "Set LLAMACPP_MMPROJ in deploy/llamacpp/paths.local.env to mmproj-NuExtract3*.gguf",
    };
  }
  return { ok: true, reason: `${path.basename(model)} + ${path.basename(mmproj)}` };
}

function checkToolchain() {
  const pnpmBin = isWin ? "pnpm.cmd" : "pnpm";
  const result = spawnSync(process.execPath, [path.join(ROOT, "scripts/check-toolchain.mjs")], {
    cwd: ROOT,
    encoding: "utf8",
    shell: false,
    env: {
      ...process.env,
      // So plain `node … doctor` still sees pnpm when Corepack/PATH is set.
      npm_config_user_agent:
        process.env.npm_config_user_agent ||
        (() => {
          const v = spawnSync(pnpmBin, ["--version"], {
            cwd: ROOT,
            encoding: "utf8",
            shell: isWin,
          });
          const ver = (v.stdout || "").trim();
          return ver ? `pnpm/${ver} node/${process.versions.node}` : undefined;
        })(),
    },
  });
  if (result.status === 0) return { ok: true, detail: (result.stdout || "").trim() || "ok" };
  const detail = (result.stderr || result.stdout || "Node/pnpm mismatch").trim().split(/\r?\n/)[0];
  return { ok: false, detail };
}

function hubImagesPresent() {
  const missing = [BACKEND_IMAGE, WEB_IMAGE].filter(
    (ref) => spawnSync("docker", ["image", "inspect", ref], { stdio: "ignore" }).status !== 0
  );
  return missing.length === 0
    ? { ok: true, detail: `${BACKEND_IMAGE.split("/").pop()} + ${WEB_IMAGE.split("/").pop()}` }
    : { ok: false, detail: `missing ${missing.join(", ")} — run: pnpm platform setup` };
}

function llamaServerVersion(exe) {
  const r = spawnSync(exe, ["--version"], { encoding: "utf8", shell: false, timeout: 15_000 });
  const text = `${r.stdout || ""}${r.stderr || ""}`;
  if (r.status === 0 || text.includes("version")) {
    return { ok: true, detail: (text.trim().split(/\r?\n/)[0] || "ok").slice(0, 80) };
  }
  return { ok: false, detail: "llama-server --version failed" };
}

/**
 * Single preflight for everything needed before starting the platform.
 * Used by `pnpm platform doctor` and automatically by `pnpm platform` / bootstrap.
 * Checks prerequisites (tools, files, images, ports), not that NuExtract loads in VRAM.
 */
function preflight({ quietOk = false } = {}) {
  console.log("\n=== Repody platform preflight ===\n");
  copyEnvFiles();
  const rows = [];
  const toolchain = checkToolchain();
  rows.push({
    name: "Node / pnpm",
    ok: toolchain.ok,
    state: toolchain.detail.replace(/^ok:\s*/i, ""),
    required: true,
    fix: "Install Node 24 + corepack enable (pnpm 12.5.1)",
  });

  const dockerOk = spawnSync("docker", ["info"], { stdio: "ignore" }).status === 0;
  rows.push({
    name: "Docker Desktop",
    ok: dockerOk,
    state: dockerOk ? "ok" : "not running",
    required: true,
    fix: "Start Docker Desktop, wait until ready",
  });

  const hub = dockerOk ? hubImagesPresent() : { ok: false, detail: "docker not running" };
  rows.push({
    name: "Hub images",
    ok: hub.ok,
    state: hub.detail,
    required: true,
    fix: "pnpm platform setup",
  });

  const llama = findExecutable("llama-server");
  const llamaRun = llama ? llamaServerVersion(llama) : { ok: false, detail: "missing" };
  rows.push({
    name: "llama-server",
    ok: llamaRun.ok,
    state: llamaRun.ok ? llamaRun.detail : `${llamaRun.detail} — ${llamaInstallHint()}`,
    required: opts.withNuextract,
    fix: llamaInstallHint(),
  });

  const nue = nuextractConfigured();
  rows.push({
    name: "NuExtract3 GGUFs",
    ok: nue.ok,
    state: nue.reason,
    required: opts.withNuextract,
    fix: "Download NuExtract3 + mmproj (pnpm llamacpp:download or https://huggingface.co/numind/NuExtract3-GGUF), then set LLAMACPP_MODEL + LLAMACPP_MMPROJ in deploy/llamacpp/paths.local.env",
  });

  for (const [name, file] of [
    ["backend/.env", BACKEND_ENV],
    [".env.local", AUTH_ENV],
  ]) {
    const ok = fs.existsSync(file);
    rows.push({
      name,
      ok,
      state: ok ? "ok" : "missing",
      required: true,
      fix: "pnpm platform setup",
    });
  }

  // Ports used by the stack + NuExtract. Not required, so a leftover stack can be restarted.
  const ports = [
    [3000, "UI"],
    [8000, "API"],
    [8080, "Keycloak"],
    [8081, "NuExtract"],
  ];
  const busy = busyPorts(ports.map(([port]) => port));
  for (const [port, label] of ports) {
    const free = !busy.has(port);
    rows.push({
      name: `Port ${port}`,
      ok: free,
      state: free ? `free (${label})` : `in use (${label}) — pnpm platform stop if leftover`,
      required: false,
      fix: `Free port ${port} or: pnpm platform stop`,
    });
  }

  for (const row of rows) {
    const mark = row.ok ? "ok" : row.required ? "!!" : "--";
    console.log(`  [${mark}] ${row.name.padEnd(18)} ${row.state}`);
  }
  console.log(
    "\nScope: tools, Hub images, NuExtract GGUF files, env. Not checked: VRAM/load success, Keycloak login, extraction E2E.\n"
  );

  const failed = rows.filter((row) => !row.ok && row.required);
  if (failed.length) {
    console.log("Fix required items, then re-run:\n");
    for (const row of failed) console.log(`  • ${row.name}: ${row.fix}`);
    console.log("\nOr: pnpm platform -- --platform-only   # containers only (skip host model)\n");
    process.exit(1);
  }
  if (!quietOk) console.log("Preflight OK — ready to start.\n");
}

function setup() {
  console.log("── Repody platform setup (once) ───────────────────────────────\n");
  copyEnvFiles();
  patchBackendEnv();
  const dockerOk = spawnSync("docker", ["info"], { stdio: "ignore" }).status === 0;
  console.log(`Docker:       ${dockerOk ? "ok" : "NOT RUNNING — start Docker Desktop"}`);
  console.log(
    `llama-server: ${findExecutable("llama-server") || `missing — ${llamaInstallHint()}`}`
  );

  if (!dockerOk) {
    console.warn("\nwarn: skipped image pull — start Docker Desktop, then: pnpm platform setup");
  } else if (opts.skipPull) {
    console.log("\n(--no-pull) skipped Hub image pull");
  } else {
    console.log("\n── Pull Hub images ──────────────────────────────────────────");
    run("docker", ["pull", BACKEND_IMAGE], { inherit: true });
    run("docker", ["pull", WEB_IMAGE], { inherit: true });
  }

  console.log(`
Setup done. Next:
  # Download NuExtract GGUFs (pnpm llamacpp:download) — see deploy/llamacpp/README.md
  # Set LLAMACPP_MODEL + LLAMACPP_MMPROJ in deploy/llamacpp/paths.local.env
  pnpm platform
`);
}

async function up() {
  preflight({ quietOk: true });
  patchBackendEnv();
  console.log(
    `Plan: Hub images  NuExtract=${opts.withNuextract ? "on (host)" : "off"}  Observability=${opts.withObs ? "on" : "off"}`
  );

  const composeEnv = {
    REPODY_PULL_POLICY: opts.skipPull ? "never" : process.env.REPODY_PULL_POLICY || "missing",
  };
  if (opts.withObs) {
    console.log("\n── Observability (Grafana · Loki · Tempo · Bugsink) ─────────");
    run("docker", composeArgs("--profile", "observability", "up", "-d", "--no-build"), {
      inherit: true,
      allowFail: true,
      env: composeEnv,
    });
  }

  // Host model first so workers never race a cold endpoint; Compose then waits on healthchecks.
  if (opts.withNuextract) {
    console.log("\n── NuExtract (host) ──────────────────────────────────────────");
    llamaServe("serve", { allowFail: true });
  }

  console.log("\n── Start Hub platform (waits for healthchecks) ───────────────");
  run(
    "docker",
    composeArgs(
      "up",
      "-d",
      "--wait",
      "--wait-timeout",
      "180",
      "--pull",
      opts.skipPull ? "never" : "missing",
      "--no-build",
      "postgres",
      "redis",
      "minio",
      "keycloak",
      "api",
      "web",
      "worker-extract",
      "worker-fast"
    ),
    { inherit: true, env: composeEnv }
  );

  await status();
  console.log(`
╔══════════════════════════════════════════════════════════════╗
║  Repody platform — ready                                     ║
╚══════════════════════════════════════════════════════════════╝

  UI          http://localhost:3000
  API         http://localhost:8000
  Keycloak    http://localhost:8080   (admin / admin)
  Sign-in     operator@repody.local / repody-dev
  Extraction  ${opts.withNuextract ? "repody:vlm (NuExtract)" : "(platform only)"}
${
  opts.withObs
    ? `
  Grafana     http://localhost:3030   (anon Admin — Loki/Tempo)
  Bugsink     http://localhost:8090   (admin@repody.local / repody-dev)
              Create a project → set BUGSINK_DSN in backend/.env → recreate api
`
    : ""
}
  Use localhost (not 127.0.0.1) in the browser for auth.

  pnpm platform status
  pnpm platform logs      # tail API / web / workers
  pnpm platform stop
`);
}

async function status() {
  const checks = [
    ["API", "http://127.0.0.1:8000/v1/healthz"],
    ["UI", "http://127.0.0.1:3000"],
    ["Keycloak", "http://127.0.0.1:8080"],
    ["NuExtract", "http://127.0.0.1:8081/v1/models"],
    ["Grafana", "http://127.0.0.1:3030"],
    ["Bugsink", "http://127.0.0.1:8090"],
  ];
  console.log("\n=== Repody platform status ===\n");
  for (const [name, url] of checks) {
    const { ok } = await fetchProbe(url, 2500);
    console.log(`  [${ok ? "ok" : "--"}] ${name.padEnd(10)} ${url}`);
  }
  console.log("\n  Logs:  pnpm platform logs");
  console.log('  Grafana Explore → Loki {container=~"repody-.*"}\n');
}

function logs() {
  console.log("Tailing API + web + workers (Ctrl+C to stop)…\n");
  run(
    "docker",
    composeArgs(
      "--profile",
      "workers",
      "logs",
      "-f",
      "--tail",
      "200",
      "api",
      "web",
      "worker-extract",
      "worker-fast"
    ),
    { inherit: true, allowFail: true }
  );
}

function stop() {
  console.log("Stopping host NuExtract + Hub Compose stack…");
  llamaServe("stop", { allowFail: true });
  run(
    "docker",
    composeArgs("--profile", "workers", "--profile", "observability", "down", "--remove-orphans"),
    { inherit: true, allowFail: true }
  );
  console.log("Stopped. Start again with: pnpm platform");
}

const commands = {
  help: printHelp,
  setup,
  bootstrap: async () => {
    setup();
    await up();
  },
  doctor: () => preflight(),
  up,
  status,
  logs,
  stop,
};
if (flags.has("--help") || flags.has("-h")) printHelp();
else if (commands[command]) await commands[command]();
else {
  console.error(`Unknown command: ${command}\n`);
  printHelp();
  process.exit(2);
}
