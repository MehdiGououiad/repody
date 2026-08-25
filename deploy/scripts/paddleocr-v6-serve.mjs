#!/usr/bin/env node
/**
 * PP-OCRv6 Basic Serving — official PaddleX OCR pipeline.
 *
 * Follows:
 *   https://www.paddleocr.ai/latest/en/version3.x/inference_deployment/serving/serving.html
 *   https://www.paddleocr.ai/latest/en/version3.x/pipeline_usage/OCR.html
 *
 * Official flow:
 *   1) paddlex --install serving
 *   2) paddlex --serve --pipeline <OCR|config.yaml> [--host] [--port] [--device]
 *   3) Client POST /ocr with { file, fileType }
 *
 * Usage: node deploy/scripts/paddleocr-v6-serve.mjs install|serve|stop|verify
 */
import { spawn, spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { fetchProbe, killListenerPort, parseEnvFile, resolveExecutable } from "./runtime-env.mjs";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const BACKEND = path.join(ROOT, "backend");
const BACKEND_ENV = path.join(BACKEND, ".env");
const LOG_DIR = path.join(ROOT, ".logs");
const PIPELINE_CONFIG = path.join(ROOT, "deploy/paddleocr-v6/OCR.yaml");
const PORT = Number(process.env.AUDIT_PADDLEOCR_V6_PORT || process.env.PADDLEOCR_V6_PORT || 8868);
const HOST = (
  process.env.AUDIT_PADDLEOCR_V6_HOST ||
  process.env.PADDLEOCR_V6_HOST ||
  "0.0.0.0"
).trim();
const DEVICE = (
  process.env.AUDIT_PADDLEOCR_V6_DEVICE ||
  process.env.PADDLEOCR_V6_DEVICE ||
  ""
).trim();
const USE_HPIP = ["1", "true", "yes"].includes(
  (process.env.AUDIT_PADDLEOCR_V6_USE_HPIP || process.env.PADDLEOCR_V6_USE_HPIP || "")
    .trim()
    .toLowerCase()
);
// Official high-performance inference ships for Linux x86-64 only.
const HPIP_SUPPORTED = process.platform === "linux" && process.arch === "x64";
// Optional `--hpi_config` JSON, e.g. '{"backend":"onnxruntime"}' (official serving flag).
const HPI_CONFIG = (
  process.env.AUDIT_PADDLEOCR_V6_HPI_CONFIG ||
  process.env.PADDLEOCR_V6_HPI_CONFIG ||
  ""
).trim();
const BASE = (process.env.AUDIT_PADDLEOCR_V6_BASE_URL || `http://127.0.0.1:${PORT}`).replace(
  /\/$/,
  ""
);

function uvBin() {
  return resolveExecutable("uv");
}

function buildServeArgs() {
  const pipeline = fs.existsSync(PIPELINE_CONFIG) ? PIPELINE_CONFIG : "OCR";
  // Prefer `python -m paddlex` — `uv run paddlex` can fail with "program not found"
  // right after install until console scripts are refreshed on PATH.
  const args = [
    "run",
    "python",
    "-m",
    "paddlex",
    "--serve",
    "--pipeline",
    pipeline,
    "--host",
    HOST,
    "--port",
    String(PORT),
  ];
  if (DEVICE) {
    args.push("--device", DEVICE);
  }
  if (USE_HPIP && HPIP_SUPPORTED) {
    args.push("--use_hpip");
    if (HPI_CONFIG) {
      args.push("--hpi_config", HPI_CONFIG);
    }
  }
  return args;
}

/**
 * Cheap liveness probe.
 *
 * `file` is required by the official POST /ocr schema, so an empty body must come
 * back as a 4xx validation error. That proves the app and route are wired without
 * paying for a pipeline run. 5xx or a missing route means the server is broken,
 * not ready.
 */
async function probeAlive(timeoutMs = 3000) {
  const res = await fetchProbe(`${BASE}/ocr`, timeoutMs, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: "{}",
  });
  if (!res.status) return { alive: false, detail: res.detail };
  if (res.status === 404) return { alive: false, detail: "POST /ocr not routed (404)" };
  if (res.status >= 500) return { alive: false, detail: `HTTP ${res.status}: ${res.detail}` };
  return { alive: true, detail: `HTTP ${res.status}` };
}

async function waitForOcr({ timeoutMs = 300_000 } = {}) {
  const started = Date.now();
  let last = "no response";
  while (Date.now() - started < timeoutMs) {
    const probe = await probeAlive();
    if (probe.alive) return { ready: true, detail: probe.detail };
    last = probe.detail;
    await new Promise((r) => setTimeout(r, 2000));
  }
  return { ready: false, detail: last };
}

/** Official POST /ocr request — returns the parsed envelope. */
async function postOcr(payload, timeoutMs) {
  const res = await fetch(`${BASE}/ocr`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(payload),
    signal: AbortSignal.timeout(timeoutMs),
  });
  const text = await res.text();
  let body = null;
  try {
    body = JSON.parse(text);
  } catch {
    body = null;
  }
  return { status: res.status, body, raw: text.slice(0, 240) };
}

function runUv(args, label) {
  console.log(label);
  const result = spawnSync(uvBin(), args, {
    cwd: BACKEND,
    stdio: "inherit",
    shell: false,
    env: { ...process.env },
  });
  if (result.status !== 0) {
    process.exit(result.status || 1);
  }
}

function paddlexServingReady() {
  const result = spawnSync(
    uvBin(),
    ["run", "python", "-c", "import paddle, paddlex, fastapi, uvicorn"],
    {
      cwd: BACKEND,
      encoding: "utf8",
      shell: false,
      stdio: ["ignore", "pipe", "pipe"],
      env: { ...process.env },
    }
  );
  return result.status === 0;
}

/** Install only when the official serving stack is missing (called from serve). */
function ensureInstalled() {
  if (process.env.REPODY_PADDLEOCR_SKIP_INSTALL === "1") return;
  if (paddlexServingReady()) return;
  console.log("PP-OCRv6 serving deps not found — installing into backend uv env (once)…");
  install();
}

function install() {
  // Official docs:
  //   https://www.paddleocr.ai/latest/en/version3.x/paddlepaddle_installation.html
  //   https://www.paddleocr.ai/latest/en/version3.x/installation.html
  //   https://www.paddleocr.ai/latest/en/version3.x/inference_deployment/serving/serving.html
  runUv(
    [
      "pip",
      "install",
      "paddlepaddle==3.2.0",
      "--index-url",
      "https://www.paddlepaddle.org.cn/packages/stable/cpu/",
      "--extra-index-url",
      "https://pypi.org/simple",
    ],
    "Installing PaddlePaddle 3.2.0 (official CPU wheel)…"
  );
  runUv(["pip", "install", "paddleocr"], "Installing paddleocr (pulls paddlex)…");

  // `paddlex --install serving` installs the `serving` extra by shelling out to
  // `python -m pip`, which fails inside uv venvs. PaddleX documents
  // `pip install "paddlex[serving]"` as the equivalent, so install the extra
  // directly and get all nine packages instead of a hand-picked subset.
  runUv(
    ["pip", "install", "paddlex[serving]"],
    "Installing the serving extra (paddlex[serving] == `paddlex --install serving`)…"
  );

  if (USE_HPIP) {
    // High-performance inference needs its own plugin; the flag alone is a no-op.
    // Official support is Linux x86-64 only.
    if (process.platform === "linux" && process.arch === "x64") {
      runUv(
        ["run", "python", "-m", "paddlex", "--install", "hpi-cpu"],
        "Installing the official HPIP CPU plugin…"
      );
      runUv(
        ["run", "python", "-m", "paddlex", "--install", "paddle2onnx"],
        "Installing the official Paddle2ONNX plugin…"
      );
    } else {
      console.warn(
        `HPIP requested but unsupported on ${process.platform}/${process.arch} ` +
          "(official support: linux x86-64). Skipping plugin install."
      );
    }
  }
  console.log("PP-OCRv6 install finished.");
}

async function serve() {
  ensureInstalled();

  const already = await probeAlive(2000);
  if (already.alive) {
    console.log(`PP-OCRv6 already listening on ${BASE}`);
    await verify();
    maybeStartQwenCompanion();
    return;
  }

  fs.mkdirSync(LOG_DIR, { recursive: true });
  const outLog = path.join(LOG_DIR, "paddleocr-v6.out.log");
  const errLog = path.join(LOG_DIR, "paddleocr-v6.err.log");
  const args = buildServeArgs();

  console.log(`Starting PP-OCRv6 Basic Serving on ${HOST}:${PORT} …`);
  console.log(`  pipeline: ${args[args.indexOf("--pipeline") + 1]}`);
  if (DEVICE) console.log(`  device:   ${DEVICE}`);
  if (USE_HPIP && HPIP_SUPPORTED) console.log("  hpip:     enabled (--use_hpip)");
  else if (USE_HPIP) {
    console.warn(
      `  hpip:     requested but unsupported on ${process.platform}/${process.arch} — ignored`
    );
  }
  console.log(`  logs:     ${LOG_DIR}`);
  console.log(
    `  docs:     https://www.paddleocr.ai/latest/en/version3.x/inference_deployment/serving/serving.html`
  );

  const child = spawn(uvBin(), args, {
    cwd: BACKEND,
    detached: true,
    stdio: ["ignore", fs.openSync(outLog, "a"), fs.openSync(errLog, "a")],
    shell: false,
    env: { ...process.env, PYTHONUNBUFFERED: "1" },
  });
  child.unref();

  const ready = await waitForOcr();
  if (!ready.ready) {
    console.error(`Timed out waiting for PP-OCRv6 at ${BASE}/ocr — ${ready.detail}`);
    console.error(
      `Check ${errLog}. If serve fails, re-run serve (auto-install) or: node deploy/scripts/paddleocr-v6-serve.mjs install`
    );
    process.exit(1);
  }
  console.log("PP-OCRv6 is up (official POST /ocr).");
  // verify() issues a real POST /ocr, which also loads the pipeline weights, so
  // there is no separate warmup pass here.
  await verify();
  maybeStartQwenCompanion();
}

function paddleocrQwenEnabledInEnv() {
  if (!fs.existsSync(BACKEND_ENV)) return true;
  const env = parseEnvFile(BACKEND_ENV);
  const raw = (env.AUDIT_PADDLEOCR_QWEN_ENABLED || "true").trim().toLowerCase();
  return raw !== "false" && raw !== "0" && raw !== "no";
}

function maybeStartQwenCompanion() {
  if (!paddleocrQwenEnabledInEnv()) return;
  console.log("Starting Qwen3.5 companion for paddleocr:qwen …");
  spawnSync(process.execPath, ["deploy/scripts/research/qwen35-serve.mjs", "serve"], {
    cwd: ROOT,
    stdio: "inherit",
    shell: false,
  });
}

/** Exercise the documented POST /ocr contract end to end, not just liveness. */
async function verify() {
  const url = `${BASE}/ocr`;
  const alive = await probeAlive(5000);
  if (!alive.alive) {
    console.error(`PP-OCRv6 not reachable at ${url}: ${alive.detail}`);
    process.exit(1);
  }

  let res;
  try {
    res = await postOcr({ file: WARMUP_PNG_B64, fileType: 1, visualize: false }, 300_000);
  } catch (error) {
    console.error(
      `PP-OCRv6 contract check failed: ${error instanceof Error ? error.message : error}`
    );
    process.exit(1);
  }
  if (res.status !== 200 || !res.body) {
    console.error(`PP-OCRv6 contract check got HTTP ${res.status}: ${res.raw}`);
    process.exit(1);
  }
  if (res.body.errorCode !== 0) {
    console.error(`PP-OCRv6 errorCode ${res.body.errorCode}: ${res.body.errorMsg || res.raw}`);
    process.exit(1);
  }
  if (!Array.isArray(res.body.result?.ocrResults)) {
    console.error(`PP-OCRv6 response missing result.ocrResults: ${res.raw}`);
    process.exit(1);
  }
  console.log(`PP-OCRv6 OK — ${url} returned errorCode 0 with result.ocrResults`);
  console.log(
    "  Client contract: POST /ocr { file, fileType, visualize, " +
      "useDocOrientationClassify, useDocUnwarping, useTextlineOrientation }"
  );
}

/** 1×1 PNG — loads pipeline weights without a real document. */
const WARMUP_PNG_B64 =
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==";

async function warmup() {
  const url = `${BASE}/ocr`;
  console.log(`Warming PP-OCRv6 at ${url}…`);
  const started = Date.now();
  let res;
  try {
    res = await postOcr({ file: WARMUP_PNG_B64, fileType: 1, visualize: false }, 300_000);
  } catch (error) {
    console.error(`PP-OCRv6 warmup failed: ${error instanceof Error ? error.message : error}`);
    process.exit(1);
  }
  if (res.status !== 200 || res.body?.errorCode !== 0) {
    console.error(`PP-OCRv6 warmup HTTP ${res.status}: ${res.body?.errorMsg || res.raw}`);
    process.exit(1);
  }
  console.log(`PP-OCRv6 warmup OK — errorCode 0 in ${Date.now() - started}ms`);
}

function stop() {
  killListenerPort(PORT);
  console.log(`Stopped PP-OCRv6 on :${PORT} (if it was running).`);
}

const cmd = process.argv[2] || "serve";
if (cmd === "install") install();
else if (cmd === "serve") void serve();
else if (cmd === "stop") stop();
else if (cmd === "verify") void verify();
else if (cmd === "warmup") void warmup();
else {
  console.error(
    "Usage: node deploy/scripts/paddleocr-v6-serve.mjs install|serve|stop|verify|warmup"
  );
  process.exit(2);
}
