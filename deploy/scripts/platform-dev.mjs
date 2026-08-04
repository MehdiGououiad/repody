#!/usr/bin/env node
/**
 * Repody local platform CLI (Windows + macOS + Linux) — same Hub images everywhere.
 *
 *   pnpm platform setup     # once
 *   pnpm platform           # pull images + start stack + default models
 *   pnpm platform -- --with-nuextract
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

const opts = {
  withNuextract: flags.has("--with-nuextract") || flags.has("--nuextract"),
  withGlm: flags.has("--with-glm") || flags.has("--glmocr") || flags.has("--glm"),
  noPaddle: flags.has("--no-paddle") || flags.has("--no-ocr"),
  noQwen: flags.has("--no-qwen") || flags.has("--no-qwen35"),
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
  2) pnpm platform setup     # once — env files + pull Hub images
  3) pnpm platform           # start platform + default models
  4) pnpm platform status    # health
  5) pnpm platform stop      # tear down

Commands:
  up         Start Hub platform + default models   [default]
  setup      Once: env / paths + pull Hub images
  bootstrap  setup + up (new machine after git clone / pnpm install)
  doctor     Check Docker, llama-server, uv, env
  status     Probe services
  stop       Stop host models + Compose
  help       This help

Options (pnpm platform -- … / pnpm platform setup -- …):
  --with-nuextract   Also start NuExtract (:8081)
  --with-glm         Also start GLM-OCR (:8083, experimental)
  --no-paddle        Skip PP-OCRv6
  --no-qwen          Skip Qwen
  --platform-only    Containers only (no host models)
  --no-pull          Do not docker pull (setup + up)

Default extraction: paddleocr:qwen  (PP-OCR :8868 + Qwen :8084)
Images: mehdigououiad/repody-backend:0.1.0 · mehdigououiad/repody-web:0.1.0

Guide: docs/deploy/LOCAL.md
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
  const wantQwen = !opts.noQwen && wantPaddle;
  setEnvKeys(BACKEND_ENV, {
    AUDIT_REPODY_VLM_ENABLED: opts.withNuextract ? "true" : "false",
    AUDIT_GLM_OCR_ENABLED: opts.withGlm ? "true" : "false",
    AUDIT_PADDLEOCR_V6_ENABLED: wantPaddle ? "true" : "false",
    AUDIT_PADDLEOCR_QWEN_ENABLED: wantQwen ? "true" : "false",
    AUDIT_QWEN35_BASE_URL: "http://127.0.0.1:8084/v1",
    AUDIT_PADDLEOCR_V6_BASE_URL: "http://127.0.0.1:8868",
    AUDIT_LLAMACPP_BASE_URL: "http://127.0.0.1:8081/v1",
    AUDIT_OTEL_ENABLED: "false",
  });
}

function composeArgs(...parts) {
  return [
    "compose",
    "-f",
    "compose.yaml",
    "-f",
    "compose.portable.yaml",
    "--env-file",
    "backend/.env",
    ...parts,
  ];
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
  const qwenSrc =
    isDarwin && fs.existsSync(QWEN_MAC_EXAMPLE) ? QWEN_MAC_EXAMPLE : QWEN_EXAMPLE;
  copyIfMissing(qwenSrc, QWEN_PATHS, "deploy/research/qwen35/paths.local.env");
  const llamaSrc =
    isDarwin && fs.existsSync(LLAMA_MAC_EXAMPLE) ? LLAMA_MAC_EXAMPLE : LLAMA_EXAMPLE;
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
      reason: "Set LLAMACPP_MODEL in deploy/llamacpp/paths.local.env to a NuExtract GGUF path",
    };
  }
  if (!mmproj || !fs.existsSync(mmproj)) {
    return {
      ok: false,
      reason: "Set LLAMACPP_MMPROJ in deploy/llamacpp/paths.local.env to the mmproj GGUF path",
    };
  }
  return { ok: true, reason: `${path.basename(model)} + mmproj` };
}

function logPlan() {
  const paddle = opts.noPaddle ? "off" : "on";
  const qwen = opts.noQwen || opts.noPaddle ? "off" : "on (host)";
  const nue = opts.withNuextract ? "on (host)" : "off";
  const glm = opts.withGlm ? "on (experimental)" : "off";
  console.log(`Plan: Hub images  PP-OCR=${paddle}  Qwen=${qwen}  NuExtract=${nue}  GLM=${glm}`);
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
  console.log(
    `llama-server: ${whichBin("llama-server") || `missing — ${llamaInstallHint()}`}`,
  );
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
  ${whichBin("llama-server") ? "" : `${llamaInstallHint()}\n  `}pnpm platform

PP-OCR Python deps install automatically on first OCR start.
Optional NuExtract: edit deploy/llamacpp/paths.local.env
  then: pnpm platform -- --with-nuextract
`);
}

async function doctor() {
  console.log("\n=== Repody platform doctor ===\n");
  const rows = [];
  const docker = spawnSync("docker", ["info"], { encoding: "utf8" });
  rows.push(["Docker", docker.status === 0 ? "ok" : "fail"]);
  rows.push(["llama-server", whichBin("llama-server") ? "ok" : "fail"]);
  rows.push(["uv", whichBin("uv") ? "ok" : "fail"]);
  rows.push(["backend/.env", fs.existsSync(BACKEND_ENV) ? "ok" : "missing"]);
  rows.push([".env.local", fs.existsSync(AUTH_ENV) ? "ok" : "missing"]);
  rows.push(["qwen paths", fs.existsSync(QWEN_PATHS) ? "ok" : "missing"]);
  const nue = nuextractConfigured();
  rows.push(["NuExtract GGUF", nue.ok ? "ok" : `skip (${nue.reason})`]);
  for (const [name, state] of rows) {
    const mark = state === "ok" ? "ok" : state.startsWith("skip") ? "--" : "!!";
    console.log(`  [${mark}] ${name.padEnd(16)} ${state}`);
  }
  console.log("");
  if (rows.some(([, s]) => s === "fail" || s === "missing")) {
    console.log("Fix gaps with: pnpm platform setup\n");
    process.exit(1);
  }
}

async function up() {
  const docker = spawnSync("docker", ["info"], { encoding: "utf8" });
  if (docker.status !== 0) {
    console.error("Docker is not running. Start Docker Desktop, then: pnpm platform");
    process.exit(1);
  }

  copyIfMissing(COMPOSE_ENV_EXAMPLE, BACKEND_ENV, "backend/.env");
  copyIfMissing(AUTH_ENV_EXAMPLE, AUTH_ENV, ".env.local");
  ensureInferencePaths();
  patchBackendEnv();
  logPlan();

  const needLlama = !opts.noQwen || opts.withNuextract || opts.withGlm;
  if (needLlama && !ensureLlamaServer({ required: true })) process.exit(1);

  if (opts.withNuextract) {
    const nue = nuextractConfigured();
    if (!nue.ok) {
      console.error(`\n--with-nuextract: ${nue.reason}\n`);
      process.exit(1);
    }
    console.log(`NuExtract: ${nue.reason}`);
  }

  if (opts.withGlm) {
    console.warn(
      "warn: Hub image is otel-only (no GLM SDK). Workers may lack glmocr deps.",
    );
  }

  console.log("\n── Start Hub platform ───────────────────────────────────────");
  const upArgs = [
    "up",
    "-d",
    "--no-build",
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
  const composeEnv = opts.skipPull
    ? { REPODY_PULL_POLICY: "never" }
    : { REPODY_PULL_POLICY: process.env.REPODY_PULL_POLICY || "missing" };
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

  if (!opts.noQwen && !opts.noPaddle) {
    console.log("\n── Qwen3.5 (host, paddleocr:qwen) ───────────────────────────");
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
    console.log("\n── GLM-OCR (host, experimental) ─────────────────────────────");
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
      "--no-build",
      "--pull",
      opts.skipPull ? "never" : "missing",
      "--force-recreate",
      "api",
      "worker-extract",
      "worker-fast",
    ),
    { inherit: true, allowFail: true, env: composeEnv },
  );
  await waitHttp("http://127.0.0.1:8000/v1/healthz/live", {
    label: "API :8000",
    timeoutMs: 120_000,
  });

  await status();
  const extraction = [];
  if (!opts.noPaddle && !opts.noQwen) extraction.push("paddleocr:qwen");
  else if (!opts.noPaddle) extraction.push("paddleocr:v6");
  if (opts.withNuextract) extraction.push("repody:vlm");
  if (opts.withGlm) extraction.push("glm:ocr");

  console.log(`
╔══════════════════════════════════════════════════════════════╗
║  Repody platform — ready                                     ║
╚══════════════════════════════════════════════════════════════╝

  UI          http://localhost:3000
  API         http://localhost:8000
  Keycloak    http://localhost:8080   (admin / admin)
  Sign-in     operator@repody.local / repody-dev
  Extraction  ${extraction.length ? extraction.join(" · ") : "(platform only)"}

  Use localhost (not 127.0.0.1) in the browser for auth.

  pnpm platform status
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
  run("docker", composeArgs("down", "--remove-orphans"), { inherit: true, allowFail: true });
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
else if (command === "stop") stop();
else {
  console.error(`Unknown command: ${command}\n`);
  printHelp();
  process.exit(2);
}
