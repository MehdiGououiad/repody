#!/usr/bin/env node
/**
 * Unified Compose local development — setup, stack, app, status, stop.
 *
 *   pnpm dev:setup   first-time env + migrate
 *   pnpm dev         background stack (Compose + workers + NuExtract)
 *   pnpm dev:api     foreground API only
 *   pnpm dev:app     foreground API + UI
 *   pnpm dev:all     stack then app (daily driver, one terminal)
 *   pnpm dev:status  health summary
 *   pnpm dev:stop    stop API, UI, NuExtract, and full Compose stack
 *   pnpm dev:restart restart NuExtract + worker containers
 */
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { fileURLToPath } from "node:url";
import {
  fetchOk,
  fetchProbe,
  killListenerPort,
  listenerDetails,
  listenerInfos,
  parseEnvFile,
  resolveExecutable,
  runtimeEnv,
  waitForPortRelease,
} from "./runtime-env.mjs";
import { spawnPrefixed } from "../../scripts/log-prefix.mjs";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const BACKEND_ENV = path.join(ROOT, "backend/.env");
const AUTH_ENV = path.join(ROOT, ".env.local");
const COMPOSE_ENV_EXAMPLE = path.join(ROOT, "deploy/env/compose.env.example");
const AUTH_ENV_EXAMPLE = path.join(ROOT, "deploy/env.auth.example");
const LLAMA_PATHS = path.join(ROOT, "deploy/llamacpp/paths.local.env");
const LLAMA_PATHS_EXAMPLE = path.join(ROOT, "deploy/llamacpp/paths.local.env.example");
const API_PORT = Number.parseInt(process.env.REPODY_API_PORT || "8000", 10);
const API_ORIGIN = `http://127.0.0.1:${API_PORT}`;
const UI_ORIGIN = "http://127.0.0.1:3000";

const args = process.argv.slice(2);
const command = args[0] || "stack";
const flags = new Set(args.slice(1));

function run(cmd, cmdArgs, opts = {}) {
  const result = spawnSync(cmd, cmdArgs, {
    cwd: ROOT,
    encoding: "utf8",
    stdio: opts.inherit ? "inherit" : ["ignore", "pipe", "pipe"],
    shell: false,
    ...opts,
  });
  if (result.status !== 0 && !opts.allowFail) {
    if (!opts.inherit) {
      if (result.stdout?.trim()) process.stderr.write(result.stdout);
      if (result.stderr?.trim()) process.stderr.write(result.stderr);
    }
    process.exit(result.status ?? 1);
  }
  return result;
}

function apiEnv() {
  return runtimeEnv(BACKEND_ENV);
}

function uiEnv() {
  const env = runtimeEnv(path.join(ROOT, ".env"), AUTH_ENV);
  if (process.env.REPODY_API_PORT && !process.env.BACKEND_URL) {
    env.BACKEND_URL = API_ORIGIN;
    env.INTERNAL_API_URL = API_ORIGIN;
  }
  return env;
}

function inferModelAlias(modelPath, explicitAlias) {
  if (explicitAlias?.trim()) return explicitAlias.trim();
  const base = modelPath ? path.basename(modelPath, ".gguf") : "";
  if (/Q4_K_M/i.test(base)) return "nuextract3-q4_k_m";
  if (/Q8_0/i.test(base)) return "nuextract3-q8_0";
  return "nuextract3-q4_k_m";
}

/** Keep backend/.env AUDIT_VLLM_SERVED_MODEL aligned with paths.local.env. */
function syncVlmServedModel() {
  if (!fs.existsSync(BACKEND_ENV)) return;
  const paths = parseEnvFile(LLAMA_PATHS);
  const alias = inferModelAlias(paths.LLAMACPP_MODEL, paths.LLAMACPP_MODEL_ALIAS);
  let body = fs.readFileSync(BACKEND_ENV, "utf8");
  if (/^AUDIT_VLLM_SERVED_MODEL=/m.test(body)) {
    const next = body.replace(/^AUDIT_VLLM_SERVED_MODEL=.*$/m, `AUDIT_VLLM_SERVED_MODEL=${alias}`);
    if (next !== body) {
      fs.writeFileSync(BACKEND_ENV, next);
      console.log(`synced backend/.env AUDIT_VLLM_SERVED_MODEL=${alias}`);
    }
    return;
  }
  fs.appendFileSync(BACKEND_ENV, `\nAUDIT_VLLM_SERVED_MODEL=${alias}\n`);
  console.log(`added backend/.env AUDIT_VLLM_SERVED_MODEL=${alias}`);
}

function copyIfMissing(src, dest, label) {
  if (fs.existsSync(dest)) return false;
  if (!fs.existsSync(src)) {
    console.warn(`warn: missing template ${path.relative(ROOT, src)} — skip ${label}`);
    return false;
  }
  fs.mkdirSync(path.dirname(dest), { recursive: true });
  fs.copyFileSync(src, dest);
  console.log(`created ${path.relative(ROOT, dest)}`);
  return true;
}

function llamaConfigured() {
  if (!fs.existsSync(LLAMA_PATHS)) return false;
  const body = fs.readFileSync(LLAMA_PATHS, "utf8");
  return /LLAMACPP_MODEL=\S/.test(body) && !/LLAMACPP_MODEL=C:\\path/.test(body);
}

function setup() {
  copyIfMissing(COMPOSE_ENV_EXAMPLE, BACKEND_ENV, "backend/.env");
  copyIfMissing(AUTH_ENV_EXAMPLE, AUTH_ENV, ".env.local");
  copyIfMissing(LLAMA_PATHS_EXAMPLE, LLAMA_PATHS, "paths.local.env");

  run("docker", ["compose", "up", "-d"]);
  syncVlmServedModel();
  run("pnpm", ["db:migrate"], { inherit: true });

  console.log("\nSetup complete.");
  printQuickStart();
}

async function stack() {
  if (!fs.existsSync(BACKEND_ENV)) {
    console.error("backend/.env missing — run: pnpm dev:setup");
    process.exit(1);
  }

  run("docker", ["compose", "up", "-d"]);
  syncVlmServedModel();

  const workerArgs = ["compose", "--profile", "workers", "up", "-d", "--build"];
  if (flags.has("--extract-only") || flags.has("--ocr-only")) {
    workerArgs.push("worker-extract");
  } else {
    workerArgs.push("worker-extract", "worker-fast");
  }
  run("docker", workerArgs);

  const skipLlama = flags.has("--no-llama");
  if (!skipLlama) {
    if (llamaConfigured()) {
      run("node", ["deploy/scripts/llamacpp-nuextract3.mjs", "serve"], { inherit: true });
    } else {
      console.warn(
        "warn: NuExtract not configured — edit deploy/llamacpp/paths.local.env, then pnpm llamacpp:serve",
      );
    }
  }

  console.log("\nStack is up (background services).");
  printQuickStart(false);
}

function printQuickStart(includeApp = true) {
  console.log("\n--- Local dev ---");
  console.log("  UI:       http://localhost:3000");
  console.log(`  API:      http://localhost:${API_PORT}/v1/healthz`);
  console.log("  Keycloak: http://localhost:8080  (operator@repody.local / repody-dev)");
  if (includeApp) {
    console.log("\n  Foreground app:  pnpm dev:app");
    console.log("  All-in-one:      pnpm dev:all");
  }
  console.log("  Status:          pnpm dev:status");
  console.log("  Stop:            pnpm dev:stop");
}

async function status() {
  const checks = [
    ["API", `${API_ORIGIN}/v1/healthz`],
    ["UI", UI_ORIGIN],
    ["Keycloak", "http://127.0.0.1:8080"],
    ["NuExtract", "http://127.0.0.1:8081/v1/models"],
  ];

  console.log("\n=== Repody local dev status ===\n");
  for (const [name, url] of checks) {
    const probe = await fetchProbe(url, 3000);
    const result = probe.ok ? "ok" : "--";
    const statusText = probe.status ? `HTTP ${probe.status}` : "no response";
    const detail = probe.ok ? "" : ` — ${statusText}; ${probe.detail || "empty response"}`;
    console.log(`${result}  ${name.padEnd(12)} ${url} (${probe.ms}ms)${detail}`);
  }

  const apiPort = listenerDetails(API_PORT);
  if (apiPort) {
    console.log(`\nAPI port ${API_PORT} listeners:\n${apiPort}`);
  }

  const compose = run("docker", ["compose", "ps", "--format", "table {{.Name}}\t{{.Status}}"], {
    allowFail: true,
  });
  if (compose.stdout?.trim()) {
    console.log("\nCompose:\n" + compose.stdout.trim());
  } else if (compose.status !== 0) {
    console.log(
      "\nCompose: unavailable — " +
        (compose.stderr || compose.stdout || "docker compose did not return status").trim(),
    );
  }

  const workers = run(
    "docker",
    ["compose", "--profile", "workers", "ps", "--format", "table {{.Name}}\t{{.Status}}"],
    { allowFail: true },
  );
  if (workers.stdout?.trim()) {
    console.log("\nWorkers:\n" + workers.stdout.trim());
  } else if (workers.status !== 0) {
    console.log(
      "\nWorkers: unavailable — " +
        (workers.stderr || workers.stdout || "docker compose did not return status").trim(),
    );
  }

  if (!llamaConfigured()) {
    console.log("NuExtract:   paths.local.env not configured (extraction disabled)");
  }
}

function killDevApi() {
  if (process.platform === "win32") {
    spawnSync(
      "powershell",
      [
        "-NoProfile",
        "-Command",
        "Get-CimInstance Win32_Process -Filter \"name='python.exe'\" " +
          "| Where-Object { $_.CommandLine -match 'uvicorn.*audit_workbench|audit_workbench\\.main' } " +
          "| ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }; " +
          "Get-CimInstance Win32_Process -Filter \"name='uv.exe'\" " +
          "| Where-Object { $_.CommandLine -match 'uvicorn.*audit_workbench' } " +
          "| ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }",
      ],
      { encoding: "utf8", shell: false },
    );
  } else {
    spawnSync("sh", ["-c", "pkill -f 'uvicorn.*audit_workbench' 2>/dev/null || true"], { shell: false });
  }
  killListenerPort(API_PORT);
  if (!waitForPortRelease(API_PORT)) {
    const listeners = listenerInfos(API_PORT);
    const stale = listeners.some((listener) => listener.missing);
    console.warn(
      stale
        ? `warn: Windows still reports a stale listener on :${API_PORT}; use REPODY_API_PORT=8002 until Windows releases it.`
        : `warn: API port :${API_PORT} is still in use:\n${listenerDetails(API_PORT)}`,
    );
  }
}

function killDevUi() {
  killListenerPort(3000);
  if (process.platform === "win32") {
    spawnSync(
      "powershell",
      [
        "-NoProfile",
        "-Command",
        "Get-CimInstance Win32_Process -Filter \"name='node.exe'\" " +
          "| Where-Object { $_.CommandLine -match 'next[\\\\/]dist[\\\\/]bin[\\\\/]next' -and $_.CommandLine -match ' dev' } " +
          "| ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }",
      ],
      { encoding: "utf8", shell: false },
    );
    return;
  }
  spawnSync("sh", ["-c", "pkill -f 'next/dist/bin/next' 2>/dev/null || true"], { shell: false });
}

async function reset() {
  console.log("=== Full platform reset (Compose volumes + DB + seed) ===\n");
  killDevUi();
  killDevApi();
  run("node", ["deploy/scripts/llamacpp-nuextract3.mjs", "stop"], { allowFail: true, inherit: true });

  run("docker", ["compose", "--profile", "workers", "down", "--remove-orphans", "-v"], {
    inherit: true,
  });

  copyIfMissing(COMPOSE_ENV_EXAMPLE, BACKEND_ENV, "backend/.env");
  copyIfMissing(AUTH_ENV_EXAMPLE, AUTH_ENV, ".env.local");
  copyIfMissing(LLAMA_PATHS_EXAMPLE, LLAMA_PATHS, "paths.local.env");

  run("docker", ["compose", "up", "-d"], { inherit: true });
  console.log("Waiting for Postgres…");
  for (let attempt = 0; attempt < 30; attempt += 1) {
    const probe = run(
      "docker",
      ["compose", "exec", "-T", "postgres", "pg_isready", "-U", "audit", "-d", "audit_workbench"],
      { allowFail: true },
    );
    if (probe.status === 0) break;
    if (attempt === 29) {
      console.error("Postgres did not become ready in time.");
      process.exit(1);
    }
    await sleep(2000);
  }
  syncVlmServedModel();
  run("pnpm", ["db:reset"], { inherit: true });

  console.log("\nRebuilding worker pools…");
  const workerArgs = ["compose", "--profile", "workers", "up", "-d", "--build"];
  if (flags.has("--extract-only") || flags.has("--ocr-only")) {
    workerArgs.push("worker-extract");
  } else {
    workerArgs.push("worker-extract", "worker-fast");
  }
  run("docker", workerArgs, { inherit: true });

  if (!flags.has("--no-llama") && llamaConfigured()) {
    run("node", ["deploy/scripts/llamacpp-nuextract3.mjs", "serve"], { inherit: true });
  }

  console.log("\nPlatform reset complete.");
  printQuickStart();
}

function stop() {
  console.log(`Stopping host dev servers (UI :3000, API :${API_PORT}, NuExtract :8081)...`);
  killDevUi();
  killDevApi();
  run("node", ["deploy/scripts/llamacpp-nuextract3.mjs", "stop"], { allowFail: true, inherit: true });

  const downArgs = ["compose", "--profile", "workers", "down", "--remove-orphans"];
  if (flags.has("--volumes") || flags.has("-v")) {
    downArgs.push("-v");
    console.log("Removing Compose volumes (--volumes)...");
  }
  run("docker", downArgs, { inherit: true });
  console.log("Local dev stopped.");
}

function restart() {
  run("node", ["deploy/scripts/llamacpp-nuextract3.mjs", "restart"], { inherit: true });
  run("docker", ["compose", "--profile", "workers", "restart", "worker-extract"], { inherit: true });
  if (!flags.has("--extract-only") && !flags.has("--ocr-only")) {
    run("docker", ["compose", "--profile", "workers", "restart", "worker-fast"], {
      inherit: true,
      allowFail: true,
    });
  }
  console.log("NuExtract + workers restarted.");
}

async function isApiRunning() {
  return fetchOk(`${API_ORIGIN}/v1/healthz`);
}

async function isUiRunning() {
  return fetchOk(UI_ORIGIN);
}

async function app(options = {}) {
  const { forceRestartApi = false } = options;
  const backendDir = path.join(ROOT, "backend");
  const nextBin = path.join(ROOT, "node_modules/next/dist/bin/next");
  const uv = resolveExecutable("uv");
  const apiUp = !forceRestartApi && (await isApiRunning());
  const uiUp = await isUiRunning();

  if (apiUp && uiUp) {
    console.log("API and UI already running — nothing to start.");
    console.log(`  API: http://localhost:${API_PORT}`);
    console.log("  UI:  http://localhost:3000");
    return;
  }

  /** @type {import("node:child_process").ChildProcess[]} */
  const children = [];

  if (apiUp) {
    console.log(`API already running on :${API_PORT} — skipping`);
  } else {
    killDevApi();
    const apiArgs = ["run", "uvicorn", "audit_workbench.main:app", "--port", String(API_PORT)];
    if (process.platform !== "win32" || process.env.REPODY_DEV_API_RELOAD === "1") {
      apiArgs.push("--reload");
    }
    children.push(
      spawnPrefixed(
        "api",
        uv,
        apiArgs,
        { cwd: backendDir, env: apiEnv() },
      ),
    );
  }

  if (uiUp) {
    console.log("UI already running on :3000 — skipping");
  } else {
    children.push(
      spawnPrefixed("ui", process.execPath, [nextBin, "dev", "--turbo"], {
        cwd: ROOT,
        env: uiEnv(),
      }),
    );
  }

  if (children.length === 0) return;

  let exiting = false;
  function shutdown(code = 0) {
    if (exiting) return;
    exiting = true;
    for (const child of children) {
      try {
        child.kill("SIGTERM");
      } catch {
        // ignore
      }
    }
    setTimeout(() => process.exit(code), 500);
  }

  process.on("SIGINT", () => shutdown(0));
  process.on("SIGTERM", () => shutdown(0));

  for (const child of children) {
    child.on("exit", (code) => {
      if (!exiting) shutdown(code ?? 1);
    });
  }
}

async function api() {
  const backendDir = path.join(ROOT, "backend");
  const uv = resolveExecutable("uv");
  killDevApi();
  const apiArgs = ["run", "uvicorn", "audit_workbench.main:app", "--port", String(API_PORT)];
  if (process.platform !== "win32" || process.env.REPODY_DEV_API_RELOAD === "1") {
    apiArgs.push("--reload");
  }
  const child = spawnPrefixed("api", uv, apiArgs, { cwd: backendDir, env: apiEnv() });

  const shutdown = () => {
    try {
      child.kill("SIGTERM");
    } catch {
      // ignore
    }
  };
  process.on("SIGINT", shutdown);
  process.on("SIGTERM", shutdown);
  child.on("exit", (code) => process.exit(code ?? 0));
}

async function all() {
  await stack();
  console.log("\nStarting API + UI (Ctrl+C stops app processes; stack keeps running)...\n");
  killDevApi();
  await new Promise((r) => setTimeout(r, 1500));
  await app({ forceRestartApi: true });
}

async function main() {
  switch (command) {
    case "setup":
      setup();
      break;
    case "stack":
      await stack();
      break;
    case "app":
      await app();
      break;
    case "api":
      await api();
      break;
    case "all":
      await all();
      break;
    case "status":
      await status();
      break;
    case "stop":
      stop();
      break;
    case "reset":
      await reset();
      break;
    case "restart":
      restart();
      break;
    default:
      console.error(
        "Usage: local-dev.mjs setup|stack|api|app|all|status|stop|reset|restart [--no-llama] [--extract-only]",
      );
      process.exit(1);
  }
}

main();
