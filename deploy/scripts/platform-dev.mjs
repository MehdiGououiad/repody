#!/usr/bin/env node
/**
 * Repody local platform CLI (Windows + macOS + Linux) — same Hub images everywhere.
 *
 *   pnpm platform setup     # once
 *   pnpm platform           # pull images + start stack + host NuExtract (default)
 *   pnpm platform -- --with-paddle
 *   pnpm platform status | stop | doctor | help
 *
 * Images: mehdigououiad/repody-backend + repody-web (linux/amd64 + linux/arm64)
 * Overlay: compose.yaml + compose.portable.yaml
 */
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { fetchOk, fetchProbe, parseEnvFile } from "./runtime-env.mjs";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const BACKEND_ENV = path.join(ROOT, "backend/.env");
const AUTH_ENV = path.join(ROOT, ".env.local");
const COMPOSE_ENV_EXAMPLE = path.join(ROOT, "deploy/env/compose.env.example");
const AUTH_ENV_EXAMPLE = path.join(ROOT, "deploy/env.auth.example");
const QWEN_PATHS = path.join(ROOT, "deploy/research/qwen35/paths.local.env");
const QWEN_MAC_EXAMPLE = path.join(ROOT, "deploy/research/qwen35/paths.mac.env.example");
const QWEN_EXAMPLE = path.join(ROOT, "deploy/research/qwen35/paths.local.env.example");
const LLAMA_PATHS = path.join(ROOT, "deploy/llamacpp/paths.local.env");
const LLAMA_MAC_EXAMPLE = path.join(ROOT, "deploy/llamacpp/paths.mac.env.example");
const LLAMA_EXAMPLE = path.join(ROOT, "deploy/llamacpp/paths.local.env.example");

const rawArgs = process.argv.slice(2);
const flags = new Set(rawArgs.filter((a) => a.startsWith("-")));
const positionals = rawArgs.filter((a) => !a.startsWith("-"));
const command = positionals[0] || (flags.has("--help") || flags.has("-h") ? "help" : "up");
const isDarwin = process.platform === "darwin";
const isWin = process.platform === "win32";

const wantPaddle = flags.has("--with-paddle") || flags.has("--with-paddleocr");
const wantQwen =
  wantPaddle || flags.has("--with-qwen") || flags.has("--with-qwen35") || flags.has("--with-glm");
const wantGlm = flags.has("--with-glm") || flags.has("--glmocr") || flags.has("--glm");

const opts = {
  // Default host model: NuExtract (catalog repody:vlm). Opt out with --no-nuextract.
  // --with-nuextract kept as a no-op alias for older docs/scripts.
  withNuextract: !(flags.has("--no-nuextract") || flags.has("--no-vlm")),
  withGlm: wantGlm,
  // Paddle / Qwen are opt-in (--with-paddle implies Qwen for paddleocr:qwen).
  noPaddle: flags.has("--no-paddle") || flags.has("--no-ocr") || !wantPaddle,
  noQwen: flags.has("--no-qwen") || flags.has("--no-qwen35") || !wantQwen,
  // Observability (Grafana/Loki/Tempo/Bugsink) on by default for Hub platform.
  withObs: !(flags.has("--no-obs") || flags.has("--no-observability")),
  platformOnly: flags.has("--platform-only"),
  skipPull: flags.has("--no-pull"),
  help: flags.has("--help") || flags.has("-h"),
};

if (opts.platformOnly) {
  opts.noPaddle = true;
  opts.noQwen = true;
  opts.withNuextract = false;
  opts.withGlm = false;
}

function printHelp() {
  console.log(`
Repody platform CLI (same on Windows, macOS, Linux)

Flow (new PC):
  1) pnpm install && pnpm doctor
  2) Download NuExtract GGUFs → set deploy/llamacpp/paths.local.env
  3) pnpm platform setup     # once — env files + pull Hub images
  4) pnpm platform           # start platform + host NuExtract (default)
  5) pnpm platform status    # health
  6) pnpm platform stop      # tear down

Commands:
  up         Start Hub platform + default models   [default]
  setup      Once: env / paths + pull Hub images
  bootstrap  setup + up (new machine after git clone / pnpm install)
  doctor     Check everything needed before start (Node, Docker, llama-server, NuExtract3 GGUFs, env)
  status     Probe services + observability URLs
  logs       Tail API/web/worker Docker logs (admin)
  stop       Stop host models + Compose
  help       This help

Preflight: pnpm platform doctor — same checks run automatically at the start of pnpm platform.

Options (pnpm platform -- … / pnpm platform setup -- …):
  --no-nuextract     Skip host NuExtract (:8081) — default is ON → catalog repody:vlm
  --with-paddle      Also start PP-OCRv6 + Qwen → catalog paddleocr:qwen
  --with-qwen        Start Qwen only (for glm:qwen without paddle)
  --with-glm         Also start GLM-OCR (:8083) + rebuild extract worker
                     with official GlmOcr SDK → catalog glm:qwen / glm:ocr
  --no-paddle        Skip PP-OCRv6 (when using --with-paddle)
  --no-qwen          Skip Qwen
  --no-obs           Skip Grafana/Loki/Tempo/Bugsink (on by default)
  --platform-only    Containers only (no host models)
  --no-pull          Do not docker pull (setup + up)

Structured paths:
  repody:vlm       NuExtract               (default)
  paddleocr:qwen   PP-OCR → Qwen JSON     (--with-paddle)
  glm:qwen         GLM-OCR SDK → Qwen JSON (--with-glm)

Images: mehdigououiad/repody-backend:0.1.0 · mehdigouiad/repody-web:0.1.0
  (--with-glm builds local worker image repody-backend:local-glmocr)

Guide: docs/deploy/LOCAL.md · Mac: docs/deploy/MAC.md
`);
}

function run(cmd, args, runOpts = {}) {
  const result = spawnSync(cmd, args, {
    cwd: ROOT,
    encoding: "utf8",
    stdio: runOpts.inherit ? "inherit" : ["ignore", "pipe", "pipe"],
    shell: false,
    env: { ...process.env, ...runOpts.env },
  });
  if (result.status !== 0 && !runOpts.allowFail) {
    if (!runOpts.inherit) {
      if (result.stdout?.trim()) process.stderr.write(result.stdout);
      if (result.stderr?.trim()) process.stderr.write(result.stderr);
    }
    process.exit(result.status ?? 1);
  }
  return result;
}

function copyIfMissing(src, dest, label) {
  if (fs.existsSync(dest)) return false;
  if (!fs.existsSync(src)) {
    console.warn(`warn: missing example ${src}`);
    return false;
  }
  fs.mkdirSync(path.dirname(dest), { recursive: true });
  fs.copyFileSync(src, dest);
  console.log(`Created ${label}`);
  return true;
}

function setEnvKeys(filePath, sets) {
  if (!fs.existsSync(filePath)) return;
  let body = fs.readFileSync(filePath, "utf8");
  for (const [key, value] of Object.entries(sets)) {
    const re = new RegExp(`^${key}=.*$`, "m");
    if (re.test(body)) body = body.replace(re, `${key}=${value}`);
    else body += `\n${key}=${value}\n`;
  }
  fs.writeFileSync(filePath, body);
}

function patchBackendEnv() {
  const wantPaddle = !opts.noPaddle;
  const wantPaddleQwen = !opts.noQwen && wantPaddle;
  const wantGlmQwen = !opts.noQwen && opts.withGlm;
  const llamaEnv = fs.existsSync(LLAMA_PATHS) ? parseEnvFile(LLAMA_PATHS) : {};
  const servedModel =
    (llamaEnv.LLAMACPP_MODEL_ALIAS || "").trim() ||
    process.env.AUDIT_LLAMACPP_SERVED_MODEL ||
    "nuextract3-q4_k_m";
  setEnvKeys(BACKEND_ENV, {
    AUDIT_REPODY_VLM_ENABLED: opts.withNuextract ? "true" : "false",
    AUDIT_GLM_OCR_ENABLED: opts.withGlm ? "true" : "false",
    AUDIT_GLM_OCR_QWEN_ENABLED: wantGlmQwen ? "true" : "false",
    AUDIT_PADDLEOCR_V6_ENABLED: wantPaddle ? "true" : "false",
    AUDIT_PADDLEOCR_QWEN_ENABLED: wantPaddleQwen ? "true" : "false",
    AUDIT_QWEN35_BASE_URL: "http://127.0.0.1:8084/v1",
    AUDIT_PADDLEOCR_V6_BASE_URL: "http://127.0.0.1:8868",
    AUDIT_LLAMACPP_BASE_URL: "http://127.0.0.1:8081/v1",
    AUDIT_LLAMACPP_SERVED_MODEL: servedModel,
    AUDIT_GLM_OCR_BASE_URL: "http://127.0.0.1:8083/v1",
    AUDIT_OTEL_ENABLED: "false",
  });
}

function composeFileArgs() {
  const files = ["-f", "compose.yaml", "-f", "compose.portable.yaml"];
  // Hub backend is otel-only; GLM catalog needs the official SDK in the worker.
  if (opts.withGlm) {
    files.push("-f", "compose.glmocr.yaml");
  }
  return files;
}

function composeArgs(...parts) {
  return ["compose", ...composeFileArgs(), "--env-file", "backend/.env", ...parts];
}

function whichBin(name) {
  if (isWin) {
    const result = spawnSync("where.exe", [name], {
      encoding: "utf8",
      shell: false,
    });
    return (result.stdout || "").trim().split(/\r?\n/).find(Boolean) || null;
  }
  const result = spawnSync("which", [name], {
    encoding: "utf8",
    shell: false,
  });
  return (result.stdout || "").trim().split(/\r?\n/).find(Boolean) || null;
}

function llamaInstallHint() {
  if (isDarwin) return "brew install llama.cpp";
  if (isWin) return "winget install ggml.llamacpp   (or put llama-server on PATH)";
  return "install llama.cpp so llama-server is on PATH";
}

function ensureLlamaServer({ required }) {
  const found = whichBin("llama-server");
  if (found) {
    console.log(`llama-server: ${found}`);
    return true;
  }
  if (!required) return false;
  console.error(`
llama-server not found on PATH.

Install once:
  ${llamaInstallHint()}

Then re-run: pnpm platform
`);
  return false;
}

function ensureInferencePaths() {
  const qwenSrc = isDarwin && fs.existsSync(QWEN_MAC_EXAMPLE) ? QWEN_MAC_EXAMPLE : QWEN_EXAMPLE;
  copyIfMissing(qwenSrc, QWEN_PATHS, "deploy/research/qwen35/paths.local.env");
  const llamaSrc = isDarwin && fs.existsSync(LLAMA_MAC_EXAMPLE) ? LLAMA_MAC_EXAMPLE : LLAMA_EXAMPLE;
  copyIfMissing(llamaSrc, LLAMA_PATHS, "deploy/llamacpp/paths.local.env");
}

function nuextractConfigured() {
  if (!fs.existsSync(LLAMA_PATHS)) return { ok: false, reason: "paths.local.env missing" };
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
          return ver ? `pnpm/${ver} node/${process.versions.node}` : process.env.npm_config_user_agent;
        })(),
    },
  });
  if (result.status === 0) {
    return { ok: true, detail: (result.stdout || "").trim() || "ok" };
  }
  const detail = ((result.stderr || result.stdout || "Node/pnpm mismatch").trim()).split(/\r?\n/)[0];
  return { ok: false, detail };
}

function hubImagesPresent() {
  const backend = process.env.REPODY_BACKEND_IMAGE || "mehdigououiad/repody-backend:0.1.0";
  const web = process.env.REPODY_WEB_IMAGE || "mehdigououiad/repody-web:0.1.0";
  const missing = [];
  for (const ref of [backend, web]) {
    const r = spawnSync("docker", ["image", "inspect", ref], {
      encoding: "utf8",
      shell: false,
      stdio: ["ignore", "pipe", "pipe"],
    });
    if (r.status !== 0) missing.push(ref);
  }
  if (missing.length === 0) {
    return { ok: true, detail: `${backend.split("/").pop()} + ${web.split("/").pop()}` };
  }
  return {
    ok: false,
    detail: `missing ${missing.join(", ")} — run: pnpm platform setup`,
  };
}

function portFree(port) {
  if (isWin) {
    const r = spawnSync("netstat", ["-ano"], { encoding: "utf8", shell: false });
    const text = `${r.stdout || ""}\n${r.stderr || ""}`;
    const re = new RegExp(`:${port}\\s+.*?LISTENING`, "i");
    return !re.test(text);
  }
  const r = spawnSync("lsof", ["-i", `TCP:${port}`, "-sTCP:LISTEN"], {
    encoding: "utf8",
    shell: false,
  });
  // lsof exit 1 = nothing listening
  return r.status !== 0;
}

function llamaServerRuns() {
  const exe = whichBin("llama-server");
  if (!exe) return { ok: false, detail: "not on PATH" };
  const r = spawnSync(exe, ["--version"], {
    encoding: "utf8",
    shell: false,
    timeout: 15_000,
  });
  if (r.status === 0 || (r.stdout || r.stderr || "").includes("version")) {
    const line = `${r.stdout || ""}${r.stderr || ""}`.trim().split(/\r?\n/)[0] || "ok";
    return { ok: true, detail: line.slice(0, 80) };
  }
  return { ok: false, detail: "llama-server --version failed" };
}

/**
 * Single preflight for everything needed before starting the platform.
 * Used by `pnpm platform doctor` and automatically by `pnpm platform` / bootstrap.
 *
 * Checks hard prerequisites (tools, files, images, ports). Does NOT guarantee
 * that NuExtract loads in VRAM or that an extraction job succeeds — that is runtime.
 */
function preflight({ exitOnFail = true, quietOk = false } = {}) {
  console.log("\n=== Repody platform preflight ===\n");

  const needLlama = !opts.platformOnly && (opts.withNuextract || !opts.noQwen || opts.withGlm);
  const needNuextract = opts.withNuextract && !opts.platformOnly;
  const needPaddle = !opts.noPaddle && !opts.platformOnly;
  const needQwenPaths = !opts.noQwen && !opts.platformOnly;

  const rows = [];
  const toolchain = checkToolchain();
  rows.push({
    name: "Node / pnpm",
    ok: toolchain.ok,
    state: toolchain.ok ? toolchain.detail.replace(/^ok:\s*/i, "") : toolchain.detail,
    required: true,
    fix: "Install Node 24 + corepack enable (pnpm 11.7.0)",
  });

  const docker = spawnSync("docker", ["info"], { encoding: "utf8" });
  const dockerOk = docker.status === 0;
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
    fix: "pnpm platform setup  (docker pull mehdigououiad/repody-backend:0.1.0 + repody-web)",
  });

  const llama = whichBin("llama-server");
  const llamaRun = needLlama && llama ? llamaServerRuns() : { ok: Boolean(llama), detail: llama || `missing — ${llamaInstallHint()}` };
  rows.push({
    name: "llama-server",
    ok: needLlama ? llamaRun.ok : Boolean(llama),
    state: needLlama ? llamaRun.detail : llama || `optional — ${llamaInstallHint()}`,
    required: needLlama,
    fix: llamaInstallHint(),
  });

  ensureInferencePaths();
  const nue = nuextractConfigured();
  rows.push({
    name: "NuExtract3 GGUFs",
    ok: nue.ok,
    state: nue.ok ? nue.reason : nue.reason,
    required: needNuextract,
    fix: "Download NuExtract3 + mmproj from https://huggingface.co/numind/NuExtract3-GGUF → set LLAMACPP_MODEL + LLAMACPP_MMPROJ in deploy/llamacpp/paths.local.env (see deploy/llamacpp/README.md)",
  });

  rows.push({
    name: "backend/.env",
    ok: fs.existsSync(BACKEND_ENV),
    state: fs.existsSync(BACKEND_ENV) ? "ok" : "missing",
    required: true,
    fix: "pnpm platform setup",
  });
  rows.push({
    name: ".env.local",
    ok: fs.existsSync(AUTH_ENV),
    state: fs.existsSync(AUTH_ENV) ? "ok" : "missing",
    required: true,
    fix: "pnpm platform setup",
  });

  const uv = whichBin("uv");
  rows.push({
    name: "uv (PP-OCR)",
    ok: Boolean(uv),
    state: uv || "missing — https://docs.astral.sh/uv/",
    required: needPaddle,
    fix: "https://docs.astral.sh/uv/ — required for --with-paddle",
  });

  rows.push({
    name: "Qwen paths",
    ok: fs.existsSync(QWEN_PATHS),
    state: fs.existsSync(QWEN_PATHS) ? "ok" : "missing",
    required: needQwenPaths,
    fix: "pnpm platform setup (copies deploy/research/qwen35/paths.*.env.example)",
  });

  // Ports used by default Hub stack + NuExtract. Warn if busy (still required=false so
  // a leftover platform can be restarted after stop — but surface clearly).
  const ports = [
    [3000, "UI"],
    [8000, "API"],
    [8080, "Keycloak"],
    [8081, "NuExtract"],
  ];
  for (const [port, label] of ports) {
    const free = portFree(port);
    rows.push({
      name: `Port ${port}`,
      ok: free,
      state: free ? `free (${label})` : `in use (${label}) — pnpm platform stop if leftover`,
      required: false,
      fix: `Free port ${port} or: pnpm platform stop`,
    });
  }

  let failed = false;
  for (const row of rows) {
    const skip = !row.required && !row.ok;
    const mark = row.ok ? "ok" : row.required ? "!!" : "--";
    if (!row.ok && row.required) failed = true;
    const label = skip ? `${row.state}` : row.state;
    console.log(`  [${mark}] ${row.name.padEnd(18)} ${label}`);
  }

  console.log("");
  console.log(
    "Scope: tools, Hub images, NuExtract GGUF files, env. Not checked: VRAM/load success, Keycloak login, extraction E2E.\n"
  );
  if (failed) {
    console.log("Fix required items, then re-run:\n");
    for (const row of rows) {
      if (!row.ok && row.required) console.log(`  • ${row.name}: ${row.fix}`);
    }
    console.log(`
Or:
  pnpm platform -- --platform-only     # containers only (skip host models)
  pnpm platform -- --no-nuextract      # skip NuExtract requirement
  pnpm platform help
`);
    if (exitOnFail) process.exit(1);
    return false;
  }

  if (!quietOk) {
    console.log("Preflight OK — ready to start.\n");
  }
  return true;
}

function logPlan() {
  const paddle = opts.noPaddle ? "off" : "on";
  const needQwen = !opts.noQwen && (!opts.noPaddle || opts.withGlm);
  const qwen = needQwen ? "on (host)" : "off";
  const nue = opts.withNuextract ? "on (host)" : "off";
  const glm = opts.withGlm ? "on (host + local worker SDK)" : "off";
  const obs = opts.withObs ? "on" : "off";
  console.log(
    `Plan: Hub images  NuExtract=${nue}  PP-OCR=${paddle}  Qwen=${qwen}  GLM=${glm}  Observability=${obs}`
  );
}

function enableObservabilityEnv() {
  setEnvKeys(BACKEND_ENV, {
    AUDIT_OTEL_ENABLED: "true",
    AUDIT_OTEL_EXPORTER_ENDPOINT: "http://otel-collector:4318/v1/traces",
    AUDIT_OTEL_SERVICE_NAME: "repody-api",
    AUDIT_LOG_JSON: "true",
  });
}

function disableObservabilityEnv() {
  setEnvKeys(BACKEND_ENV, {
    AUDIT_OTEL_ENABLED: "false",
  });
}

function startObservabilityStack(composeEnv) {
  console.log("\n── Observability (Grafana · Loki · Tempo · Bugsink) ─────────");
  enableObservabilityEnv();
  run("docker", composeArgs("--profile", "observability", "up", "-d", "--no-build"), {
    inherit: true,
    allowFail: true,
    env: composeEnv,
  });
}

async function waitHttp(url, { timeoutMs = 180_000, label = url } = {}) {
  const started = Date.now();
  while (Date.now() - started < timeoutMs) {
    if (await fetchOk(url)) {
      console.log(`ok  ${label}`);
      return true;
    }
    await new Promise((r) => setTimeout(r, 2000));
  }
  console.error(`timeout waiting for ${label}`);
  return false;
}

function pullHubImages() {
  const backend = process.env.REPODY_BACKEND_IMAGE || "mehdigououiad/repody-backend:0.1.0";
  const web = process.env.REPODY_WEB_IMAGE || "mehdigououiad/repody-web:0.1.0";
  console.log("\n── Pull Hub images ──────────────────────────────────────────");
  console.log(`  ${backend}`);
  console.log(`  ${web}`);
  run("docker", ["pull", backend], { inherit: true });
  run("docker", ["pull", web], { inherit: true });
}

function setup() {
  console.log("── Repody platform setup (once) ───────────────────────────────\n");
  copyIfMissing(COMPOSE_ENV_EXAMPLE, BACKEND_ENV, "backend/.env");
  copyIfMissing(AUTH_ENV_EXAMPLE, AUTH_ENV, ".env.local");
  ensureInferencePaths();
  patchBackendEnv();

  const docker = spawnSync("docker", ["info"], { encoding: "utf8" });
  const dockerOk = docker.status === 0;
  console.log(`Docker:       ${dockerOk ? "ok" : "NOT RUNNING — start Docker Desktop"}`);
  console.log(`llama-server: ${whichBin("llama-server") || `missing — ${llamaInstallHint()}`}`);
  console.log(`uv:           ${whichBin("uv") || "missing — https://docs.astral.sh/uv/"}`);

  if (dockerOk && !opts.skipPull) {
    pullHubImages();
  } else if (!dockerOk) {
    console.warn("\nwarn: skipped image pull — start Docker Desktop, then: pnpm platform setup");
  } else {
    console.log("\n(--no-pull) skipped Hub image pull");
  }

  console.log(`
Setup done. Next:
  ${whichBin("llama-server") ? "" : `${llamaInstallHint()}\n  `}# Download NuExtract GGUFs — see deploy/llamacpp/README.md
  # Set LLAMACPP_MODEL + LLAMACPP_MMPROJ in deploy/llamacpp/paths.local.env
  pnpm platform

Default host model: NuExtract (repody:vlm). Optional:
  pnpm platform -- --with-paddle     # also PP-OCR + Qwen
  pnpm platform -- --with-glm        # also GLM-OCR
`);
}

async function doctor() {
  // Full preflight — same gates as `pnpm platform` before start.
  preflight({ exitOnFail: true });
}

async function up() {
  copyIfMissing(COMPOSE_ENV_EXAMPLE, BACKEND_ENV, "backend/.env");
  copyIfMissing(AUTH_ENV_EXAMPLE, AUTH_ENV, ".env.local");
  ensureInferencePaths();
  patchBackendEnv();

  // Same comprehensive check as `pnpm platform doctor`.
  preflight({ exitOnFail: true, quietOk: true });
  logPlan();

  const needLlama = !opts.noQwen || opts.withNuextract || opts.withGlm;
  if (needLlama && !ensureLlamaServer({ required: true })) process.exit(1);

  if (opts.withNuextract) {
    const nue = nuextractConfigured();
    console.log(`NuExtract: ${nue.reason}`);
  }

  const composeEnv = {
    REPODY_PULL_POLICY: opts.skipPull ? "never" : process.env.REPODY_PULL_POLICY || "missing",
    AUDIT_OTEL_ENABLED: opts.withObs ? "true" : "false",
    AUDIT_OTEL_EXPORTER_ENDPOINT: "http://otel-collector:4318/v1/traces",
    REPODY_BACKEND_EXTRAS: process.env.REPODY_BACKEND_EXTRAS || "otel,glmocr",
  };

  if (opts.withObs) {
    startObservabilityStack(composeEnv);
  } else {
    disableObservabilityEnv();
  }

  if (opts.withGlm) {
    console.log("\n── Build extract worker (official GlmOcr SDK extras) ─────────");
    run("docker", composeArgs("--profile", "workers", "build", "worker-extract"), {
      inherit: true,
      env: composeEnv,
    });
  }

  console.log("\n── Start Hub platform ───────────────────────────────────────");
  const upArgs = [
    "up",
    "-d",
    opts.withGlm ? "--build" : "--no-build",
    "postgres",
    "redis",
    "minio",
    "minio-init",
    "keycloak",
    "api",
    "web",
    "worker-extract",
    "worker-fast",
  ];
  // Images are pulled by `pnpm platform setup`. `--no-pull` forces never; otherwise refresh if missing.
  if (opts.skipPull) upArgs.splice(2, 0, "--pull", "never");
  else upArgs.splice(2, 0, "--pull", "missing");
  run("docker", composeArgs(...upArgs), { inherit: true, env: composeEnv });

  console.log("\n── Waiting for API ──────────────────────────────────────────");
  if (!(await waitHttp("http://127.0.0.1:8000/v1/healthz/live", { label: "API :8000" }))) {
    process.exit(1);
  }

  if (!opts.noPaddle) {
    console.log("\n── PP-OCRv6 (host; auto-installs deps if needed) ────────────");
    run("node", ["deploy/scripts/paddleocr-v6-serve.mjs", "serve"], {
      inherit: true,
      allowFail: true,
    });
  }

  // Qwen is the JSON stage for paddleocr:qwen and glm:qwen.
  if (!opts.noQwen && (!opts.noPaddle || opts.withGlm)) {
    console.log("\n── Qwen3.5 (host, OCR→JSON) ─────────────────────────────────");
    run("node", ["deploy/scripts/research/qwen35-serve.mjs", "serve"], {
      inherit: true,
      allowFail: true,
    });
  }

  if (opts.withNuextract) {
    console.log("\n── NuExtract (host) ─────────────────────────────────────────");
    run("node", ["deploy/scripts/llamacpp-nuextract3.mjs", "serve"], {
      inherit: true,
      allowFail: true,
    });
  }

  if (opts.withGlm) {
    console.log("\n── GLM-OCR (host llama-server) ──────────────────────────────");
    run("node", ["deploy/scripts/glmocr-serve.mjs", "serve"], {
      inherit: true,
      allowFail: true,
    });
  }

  run(
    "docker",
    composeArgs(
      "up",
      "-d",
      opts.withGlm ? "--build" : "--no-build",
      "--pull",
      opts.skipPull ? "never" : "missing",
      "--force-recreate",
      "api",
      "web",
      "worker-extract",
      "worker-fast"
    ),
    { inherit: true, allowFail: true, env: composeEnv }
  );
  await waitHttp("http://127.0.0.1:8000/v1/healthz/live", {
    label: "API :8000",
    timeoutMs: 120_000,
  });

  await status();
  const extraction = [];
  if (opts.withNuextract) extraction.push("repody:vlm");
  if (!opts.noPaddle && !opts.noQwen) extraction.push("paddleocr:qwen");
  else if (!opts.noPaddle) extraction.push("paddleocr:v6");
  if (opts.withGlm && !opts.noQwen) extraction.push("glm:qwen");
  else if (opts.withGlm) extraction.push("glm:ocr");

  console.log(`
╔══════════════════════════════════════════════════════════════╗
║  Repody platform — ready                                     ║
╚══════════════════════════════════════════════════════════════╝

  UI          http://localhost:3000
  API         http://localhost:8000
  Keycloak    http://localhost:8080   (admin / admin)
  Sign-in     operator@repody.local / repody-dev
  Extraction  ${extraction.length ? extraction.join(" · ") : "(platform only)"}
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
  pnpm platform help
`);
}

async function status() {
  const checks = [
    ["API", "http://127.0.0.1:8000/v1/healthz"],
    ["UI", "http://127.0.0.1:3000"],
    ["Keycloak", "http://127.0.0.1:8080"],
    ["PP-OCRv6", "http://127.0.0.1:8868/ocr"],
    ["Qwen3.5", "http://127.0.0.1:8084/v1/models"],
    ["NuExtract", "http://127.0.0.1:8081/v1/models"],
    ["GLM-OCR", "http://127.0.0.1:8083/v1/models"],
    ["Grafana", "http://127.0.0.1:3030"],
    ["Bugsink", "http://127.0.0.1:8090"],
  ];
  console.log("\n=== Repody platform status ===\n");
  for (const [name, url] of checks) {
    const probe =
      name === "PP-OCRv6"
        ? await fetchProbe(url, 2500, {
            method: "POST",
            headers: { "content-type": "application/json" },
            body: "{}",
          })
        : await fetchProbe(url, 2500);
    const ok =
      name === "PP-OCRv6"
        ? Boolean(probe.status && probe.status !== 404 && probe.status < 500)
        : probe.ok;
    console.log(`  [${ok ? "ok" : "--"}] ${name.padEnd(10)} ${url}`);
  }
  console.log("");
  console.log("  Logs:  pnpm platform logs");
  console.log('  Grafana Explore → Loki {container=~"repody-.*"}');
  console.log("");
}

function logs() {
  console.log("Tailing API + web + workers (Ctrl+C to stop)…\n");
  run(
    "docker",
    [
      "compose",
      ...composeFileArgs(),
      "--env-file",
      "backend/.env",
      "--profile",
      "workers",
      "logs",
      "-f",
      "--tail",
      "200",
      "api",
      "web",
      "worker-extract",
      "worker-fast",
    ],
    { inherit: true, allowFail: true }
  );
}

function stop() {
  console.log("Stopping host models + Hub Compose stack…");
  run("node", ["deploy/scripts/research/qwen35-serve.mjs", "stop"], {
    allowFail: true,
    inherit: true,
  });
  run("node", ["deploy/scripts/paddleocr-v6-serve.mjs", "stop"], {
    allowFail: true,
    inherit: true,
  });
  run("node", ["deploy/scripts/llamacpp-nuextract3.mjs", "stop"], {
    allowFail: true,
    inherit: true,
  });
  run("node", ["deploy/scripts/glmocr-serve.mjs", "stop"], {
    allowFail: true,
    inherit: true,
  });
  run(
    "docker",
    composeArgs("--profile", "workers", "--profile", "observability", "down", "--remove-orphans"),
    { inherit: true, allowFail: true }
  );
  console.log("Stopped. Start again with: pnpm platform");
}

async function bootstrap() {
  setup();
  await up();
}

if (command === "help" || opts.help) printHelp();
else if (command === "setup") setup();
else if (command === "bootstrap") void bootstrap();
else if (command === "doctor") void doctor();
else if (command === "up") void up();
else if (command === "status") void status();
else if (command === "logs") logs();
else if (command === "stop") stop();
else {
  console.error(`Unknown command: ${command}\n`);
  printHelp();
  process.exit(2);
}
