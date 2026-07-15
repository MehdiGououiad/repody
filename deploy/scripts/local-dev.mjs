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
 *   pnpm dev:observability  Grafana + Loki + Tempo + OTEL + Bugsink (optional profile)
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
import { printDevDashboard } from "./dev-dashboard.mjs";

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
const GRAFANA_ORIGIN = "http://127.0.0.1:3030";
const OTEL_HTTP_ORIGIN = "http://127.0.0.1:4318";
const BUGSINK_ORIGIN = "http://127.0.0.1:8090";
const LOG_DIR = path.join(ROOT, ".logs");
const LOG_FILE = path.join(LOG_DIR, "repody-api.log");
const OBS_ENV_FILE = path.join(ROOT, "deploy/env/observability.enabled.env");

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
  if (base && !/Q4_K_M/i.test(base)) {
    console.warn(
      `warn: expected NuExtract3-Q4_K_M.gguf (official local default); got ${base}`
    );
  }
  return "nuextract3-q4_k_m";
}

/** Keep backend/.env AUDIT_LLAMACPP_SERVED_MODEL aligned with paths.local.env. */
function syncVlmServedModel() {
  if (!fs.existsSync(BACKEND_ENV)) return;
  const paths = parseEnvFile(LLAMA_PATHS);
  const alias = inferModelAlias(paths.LLAMACPP_MODEL, paths.LLAMACPP_MODEL_ALIAS);
  let body = fs.readFileSync(BACKEND_ENV, "utf8");
  if (/^AUDIT_LLAMACPP_SERVED_MODEL=/m.test(body)) {
    const next = body.replace(/^AUDIT_LLAMACPP_SERVED_MODEL=.*$/m, `AUDIT_LLAMACPP_SERVED_MODEL=${alias}`);
    if (next !== body) {
      fs.writeFileSync(BACKEND_ENV, next);
      console.log(`synced backend/.env AUDIT_LLAMACPP_SERVED_MODEL=${alias}`);
    }
    return;
  }
  fs.appendFileSync(BACKEND_ENV, `\nAUDIT_LLAMACPP_SERVED_MODEL=${alias}\n`);
  console.log(`added backend/.env AUDIT_LLAMACPP_SERVED_MODEL=${alias}`);
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

function isObservabilityRunning() {
  const result = run("docker", ["compose", "--profile", "observability", "ps", "-q", "loki"], {
    allowFail: true,
  });
  return Boolean(result.stdout?.trim());
}

function dashboardContext() {
  return {
    apiPort: API_PORT,
    observability: wantsObservability() || isObservabilityRunning(),
    llama: llamaConfigured() && !flags.has("--no-llama"),
    extractOnly: flags.has("--extract-only"),
  };
}

async function showDevDashboard({ appRunning = false, probe = true } = {}) {
  await printDevDashboard({
    ...dashboardContext(),
    appRunning,
    probe,
    fetchProbe,
  });
}

async function waitForDevAppReady(timeoutMs = 120_000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const [api, ui] = await Promise.all([isApiRunning(), isUiRunning()]);
    if (api && ui) return true;
    await sleep(500);
  }
  return false;
}

function wantsObservability() {
  if (flags.has("--no-observability") || flags.has("--no-obs")) return false;
  if (flags.has("--observability") || flags.has("--obs")) return true;
  // Opt-in only — Grafana/Loki/Tempo/Bugsink add minutes and force-recreate workers.
  return false;
}

function wantsWorkerRebuild() {
  return (
    flags.has("--rebuild-workers") ||
    flags.has("--build") ||
    process.env.REPODY_DEV_REBUILD_WORKERS === "1"
  );
}

function phaseMs(label, startedAt) {
  const ms = Date.now() - startedAt;
  console.log(`[dev] ${label}: ${ms}ms`);
  return ms;
}

function relativeBackendLogFile() {
  return path.relative(path.join(ROOT, "backend"), LOG_FILE).replace(/\\/g, "/");
}

function writeObservabilityWorkerEnv() {
  fs.mkdirSync(path.dirname(OBS_ENV_FILE), { recursive: true });
  fs.writeFileSync(OBS_ENV_FILE, "AUDIT_OTEL_ENABLED=true\n");
}

function removeObservabilityWorkerEnv() {
  if (fs.existsSync(OBS_ENV_FILE)) fs.unlinkSync(OBS_ENV_FILE);
}

function upsertEnvLines(filePath, updates) {
  if (!fs.existsSync(filePath)) return;
  let body = fs.readFileSync(filePath, "utf8");
  for (const [key, value] of Object.entries(updates)) {
    if (new RegExp(`^${key}=`, "m").test(body)) {
      body = body.replace(new RegExp(`^${key}=.*$`, "m"), `${key}=${value}`);
    } else {
      body += `\n${key}=${value}\n`;
    }
  }
  fs.writeFileSync(filePath, body);
}

/** Enable JSON logs, OTLP traces, Loki file tail, and worker OTEL when stack is up. */
function enableObservabilityInBackendEnv() {
  fs.mkdirSync(LOG_DIR, { recursive: true });
  writeObservabilityWorkerEnv();

  if (fs.existsSync(BACKEND_ENV)) {
    upsertEnvLines(BACKEND_ENV, {
      AUDIT_LOG_JSON: "true",
      AUDIT_OTEL_ENABLED: "true",
      AUDIT_OTEL_EXPORTER_ENDPOINT: `${OTEL_HTTP_ORIGIN}/v1/traces`,
      AUDIT_OTEL_SERVICE_NAME: "repody-api",
      AUDIT_LOG_FILE: relativeBackendLogFile(),
    });
  }

  console.log("enabled observability in backend/.env (restart API to ship logs/traces)");
}

/** Turn off OTEL/Bugsink export when observability profile is not running (avoids retry spam). */
function disableObservabilityInBackendEnv() {
  removeObservabilityWorkerEnv();
  if (!fs.existsSync(BACKEND_ENV)) return;
  upsertEnvLines(BACKEND_ENV, {
    AUDIT_OTEL_ENABLED: "false",
  });
  // Comment active Bugsink DSN so Sentry SDK does not retry a down :8090.
  let body = fs.readFileSync(BACKEND_ENV, "utf8");
  if (/^BUGSINK_DSN=.+/m.test(body) && !/^#\s*BUGSINK_DSN=/m.test(body)) {
    body = body.replace(/^BUGSINK_DSN=/m, "# BUGSINK_DSN=");
    fs.writeFileSync(BACKEND_ENV, body);
  }
}

function recreateWorkersForObservability() {
  run(
    "docker",
    ["compose", "--profile", "workers", "up", "-d", "--force-recreate", "worker-extract", "worker-fast"],
    { allowFail: true },
  );
}

function observabilityStack() {
  run("docker", ["compose", "--profile", "observability", "up", "-d"]);
  enableObservabilityInBackendEnv();
  // Recreate only when explicitly requested — default path just enables OTEL env.
  if (flags.has("--recreate-workers") || wantsWorkerRebuild()) {
    recreateWorkersForObservability();
  } else {
    console.log(
      "observability env enabled — restart workers later if needed: pnpm dev:restart",
    );
  }
}

function composeDownArgs() {
  const args = ["compose", "--profile", "workers", "--profile", "observability", "down", "--remove-orphans"];
  if (flags.has("--volumes") || flags.has("-v")) args.push("-v");
  return args;
}

async function setup() {
  copyIfMissing(COMPOSE_ENV_EXAMPLE, BACKEND_ENV, "backend/.env");
  copyIfMissing(AUTH_ENV_EXAMPLE, AUTH_ENV, ".env.local");
  copyIfMissing(LLAMA_PATHS_EXAMPLE, LLAMA_PATHS, "paths.local.env");

  run("docker", ["compose", "up", "-d"]);
  syncVlmServedModel();
  run("pnpm", ["db:migrate"], { inherit: true });

  console.log("\nSetup complete.");
  await showDevDashboard({ appRunning: false, probe: false });
}

async function stack(options = {}) {
  const { suppressDashboard = false } = options;
  if (!fs.existsSync(BACKEND_ENV)) {
    console.error("backend/.env missing — run: pnpm dev:setup");
    process.exit(1);
  }

  const stackStarted = Date.now();

  let t = Date.now();
  run("docker", ["compose", "up", "-d"]);
  syncVlmServedModel();
  phaseMs("compose base", t);

  // Start NuExtract before workers so extract pool does not race a cold :8081.
  const skipLlama = flags.has("--no-llama");
  if (!skipLlama) {
    if (llamaConfigured()) {
      t = Date.now();
      run("node", ["deploy/scripts/llamacpp-nuextract3.mjs", "serve"], { inherit: true });
      phaseMs("nuextract serve+warmup", t);
    } else {
      console.warn(
        "warn: NuExtract not configured — edit deploy/llamacpp/paths.local.env, then pnpm llamacpp:serve",
      );
    }
  }

  t = Date.now();
  const workerArgs = ["compose", "--profile", "workers", "up", "-d"];
  if (wantsWorkerRebuild()) workerArgs.push("--build");
  if (flags.has("--extract-only")) {
    workerArgs.push("worker-extract");
  } else {
    workerArgs.push("worker-extract", "worker-fast");
  }
  run("docker", workerArgs);
  phaseMs(wantsWorkerRebuild() ? "workers up --build" : "workers up", t);

  if (wantsObservability()) {
    t = Date.now();
    observabilityStack();
    phaseMs("observability", t);
  } else {
    disableObservabilityInBackendEnv();
  }

  phaseMs("stack total", stackStarted);

  if (!suppressDashboard) {
    await showDevDashboard({ appRunning: false });
  }
}

async function status() {
  const checks = [
    ["API", `${API_ORIGIN}/v1/healthz`],
    ["UI", UI_ORIGIN],
    ["Keycloak", "http://127.0.0.1:8080"],
    ["NuExtract", "http://127.0.0.1:8081/v1/models"],
    ["Grafana", `${GRAFANA_ORIGIN}/api/health`],
    ["Loki", "http://127.0.0.1:3100/ready"],
    ["Tempo", "http://127.0.0.1:3200/ready"],
    ["Bugsink", `${BUGSINK_ORIGIN}/`],
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

  const obs = run(
    "docker",
    ["compose", "--profile", "observability", "ps", "--format", "table {{.Name}}\t{{.Status}}"],
    { allowFail: true },
  );
  if (obs.stdout?.trim()) {
    console.log("\nObservability:\n" + obs.stdout.trim());
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
  run("docker", ["compose", "--profile", "observability", "down", "--remove-orphans"], {
    inherit: true,
    allowFail: true,
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
  if (flags.has("--extract-only")) {
    workerArgs.push("worker-extract");
  } else {
    workerArgs.push("worker-extract", "worker-fast");
  }
  run("docker", workerArgs, { inherit: true });

  if (!flags.has("--no-llama") && llamaConfigured()) {
    run("node", ["deploy/scripts/llamacpp-nuextract3.mjs", "serve"], { inherit: true });
  }

  console.log("\nPlatform reset complete.");
  await showDevDashboard({ appRunning: false });
}

function stop() {
  console.log(`Stopping host dev servers (UI :3000, API :${API_PORT}, NuExtract :8081)...`);
  killDevUi();
  killDevApi();
  run("node", ["deploy/scripts/llamacpp-nuextract3.mjs", "stop"], { allowFail: true, inherit: true });

  const downArgs = composeDownArgs();
  if (flags.has("--volumes") || flags.has("-v")) {
    console.log("Removing Compose volumes (--volumes)...");
  }
  run("docker", downArgs, { inherit: true });
  removeObservabilityWorkerEnv();
  console.log("Local dev stopped.");
}

function restart() {
  run("node", ["deploy/scripts/llamacpp-nuextract3.mjs", "restart"], { inherit: true });
  run("docker", ["compose", "--profile", "workers", "restart", "worker-extract"], { inherit: true });
  if (!flags.has("--extract-only")) {
    run("docker", ["compose", "--profile", "workers", "restart", "worker-fast"], {
      inherit: true,
      allowFail: true,
    });
  }
  console.log("NuExtract + workers restarted.");
}

async function isApiRunning() {
  // Liveness is enough for "process up"; readiness is checked by `dev:status`.
  return fetchOk(`${API_ORIGIN}/v1/healthz/live`);
}

async function isUiRunning() {
  return fetchOk(UI_ORIGIN);
}

async function waitForInterrupt() {
  return new Promise((resolve) => {
    const onSignal = () => resolve(0);
    process.once("SIGINT", onSignal);
    process.once("SIGTERM", onSignal);
  });
}

/** Block until Ctrl+C or a foreground child exits; optionally tear down children. */
async function waitForForeground(children) {
  if (children.length === 0) {
    console.log("\n  Press Ctrl+C to close this terminal (services keep running in the background).\n");
    return waitForInterrupt();
  }

  return new Promise((resolve) => {
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
      setTimeout(() => resolve(code), 500);
    }
    process.once("SIGINT", () => shutdown(0));
    process.once("SIGTERM", () => shutdown(0));
    for (const child of children) {
      child.on("exit", (code) => {
        if (!exiting) shutdown(code ?? 1);
      });
    }
  });
}

async function app(options = {}) {
  const { forceRestartApi = false, forceRestartUi = false, keepAlive = false } = options;
  const backendDir = path.join(ROOT, "backend");
  const nextBin = path.join(ROOT, "node_modules/next/dist/bin/next");
  const uv = resolveExecutable("uv");
  const apiUp = !forceRestartApi && (await isApiRunning());
  const uiUp = !forceRestartUi && (await isUiRunning());

  if (apiUp && uiUp && !forceRestartApi) {
    await showDevDashboard({ appRunning: true });
    if (!keepAlive) return;
    console.log("\n  API + UI already running. Press Ctrl+C to exit this terminal.\n");
    await waitForInterrupt();
    return;
  }

  /** @type {import("node:child_process").ChildProcess[]} */
  const children = [];

  if (apiUp) {
    console.log(`API already running on :${API_PORT} — skipping`);
  } else {
    killDevApi();
    const apiArgs = ["run", "--extra", "otel", "uvicorn", "audit_workbench.main:app", "--port", String(API_PORT)];
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
    killDevUi();
    children.push(
      spawnPrefixed("ui", process.execPath, [nextBin, "dev", "--turbo"], {
        cwd: ROOT,
        env: uiEnv(),
      }),
    );
  }

  if (children.length === 0) {
    if (keepAlive) {
      console.log("\n  Press Ctrl+C to exit this terminal.\n");
      await waitForInterrupt();
    }
    return;
  }

  void waitForDevAppReady().then(async (ready) => {
    if (ready) {
      await showDevDashboard({ appRunning: true });
    } else {
      console.warn("warn: API or UI did not become ready in time — run: pnpm dev:status");
    }
  });

  console.log("\n  Streaming API + UI logs — Ctrl+C stops app processes (Compose stack keeps running).\n");

  const exitCode = await waitForForeground(children);
  process.exit(exitCode);
}

async function api() {
  const backendDir = path.join(ROOT, "backend");
  const uv = resolveExecutable("uv");
  killDevApi();
  const apiArgs = ["run", "--extra", "otel", "uvicorn", "audit_workbench.main:app", "--port", String(API_PORT)];
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
  await stack({ suppressDashboard: true });
  console.log("\nStarting API + UI (Ctrl+C stops app processes; stack keeps running)...\n");
  // Reuse warm processes when already healthy — avoids killing Turbopack cache.
  await app({ keepAlive: true });
}

async function main() {
  switch (command) {
    case "setup":
      await setup();
      break;
    case "stack":
      await stack();
      break;
    case "app":
      await app({ keepAlive: true });
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
    case "observability":
      observabilityStack();
      await showDevDashboard({ appRunning: await isApiRunning() && (await isUiRunning()) });
      break;
    default:
      console.error(
        "Usage: local-dev.mjs setup|stack|api|app|all|status|stop|reset|restart|observability [--no-llama] [--extract-only] [--obs] [--no-obs] [--rebuild-workers]",
      );
      process.exit(1);
  }
}

main();
