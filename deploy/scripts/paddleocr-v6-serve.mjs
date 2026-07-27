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
import { fetchProbe, killListenerPort, resolveExecutable } from "./runtime-env.mjs";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const BACKEND = path.join(ROOT, "backend");
const LOG_DIR = path.join(ROOT, ".logs");
const PIPELINE_CONFIG = path.join(ROOT, "deploy/paddleocr-v6/OCR.yaml");
const PORT = Number(process.env.AUDIT_PADDLEOCR_V6_PORT || process.env.PADDLEOCR_V6_PORT || 8868);
const HOST = (process.env.AUDIT_PADDLEOCR_V6_HOST || process.env.PADDLEOCR_V6_HOST || "0.0.0.0").trim();
const DEVICE = (process.env.AUDIT_PADDLEOCR_V6_DEVICE || process.env.PADDLEOCR_V6_DEVICE || "").trim();
const USE_HPIP = ["1", "true", "yes"].includes(
  (process.env.AUDIT_PADDLEOCR_V6_USE_HPIP || process.env.PADDLEOCR_V6_USE_HPIP || "").trim().toLowerCase(),
);
const BASE = (process.env.AUDIT_PADDLEOCR_V6_BASE_URL || `http://127.0.0.1:${PORT}`).replace(
  /\/$/,
  "",
);

function uvBin() {
  return resolveExecutable("uv");
}

function buildServeArgs() {
  const pipeline = fs.existsSync(PIPELINE_CONFIG) ? PIPELINE_CONFIG : "OCR";
  const args = [
    "run",
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
  if (USE_HPIP) {
    args.push("--use_hpip");
  }
  return args;
}

async function waitForOcr({ timeoutMs = 180_000 } = {}) {
  const started = Date.now();
  const url = `${BASE}/ocr`;
  while (Date.now() - started < timeoutMs) {
    const res = await fetchProbe(url, 3000, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: "{}",
    });
    if (res.status) return true;
    await new Promise((r) => setTimeout(r, 2000));
  }
  return false;
}

function install() {
  console.log("Installing PaddleX serving plugin (official: paddlex --install serving)…");
  const result = spawnSync(uvBin(), ["run", "paddlex", "--install", "serving", "-y"], {
    cwd: BACKEND,
    stdio: "inherit",
    shell: false,
    env: { ...process.env },
  });
  if (result.status !== 0) {
    process.exit(result.status || 1);
  }
  console.log("Serving plugin install finished.");
}

async function serve() {
  const already = await fetchProbe(`${BASE}/ocr`, 2000, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: "{}",
  });
  if (already.status) {
    console.log(`PP-OCRv6 already listening on ${BASE}`);
    await verify();
    return;
  }

  fs.mkdirSync(LOG_DIR, { recursive: true });
  const outLog = path.join(LOG_DIR, "paddleocr-v6.out.log");
  const errLog = path.join(LOG_DIR, "paddleocr-v6.err.log");
  const args = buildServeArgs();

  console.log(`Starting PP-OCRv6 Basic Serving on ${HOST}:${PORT} …`);
  console.log(`  pipeline: ${args[args.indexOf("--pipeline") + 1]}`);
  if (DEVICE) console.log(`  device:   ${DEVICE}`);
  if (USE_HPIP) console.log("  hpip:     enabled (--use_hpip)");
  console.log(`  logs:     ${LOG_DIR}`);
  console.log(`  docs:     https://www.paddleocr.ai/latest/en/version3.x/inference_deployment/serving/serving.html`);

  const child = spawn(uvBin(), args, {
    cwd: BACKEND,
    detached: true,
    stdio: ["ignore", fs.openSync(outLog, "a"), fs.openSync(errLog, "a")],
    shell: false,
    env: { ...process.env, PYTHONUNBUFFERED: "1" },
  });
  child.unref();

  const ready = await waitForOcr();
  if (!ready) {
    console.error(`Timed out waiting for PP-OCRv6 at ${BASE}/ocr — check ${errLog}`);
    console.error("If serve fails, run: pnpm paddleocr:v6:install");
    process.exit(1);
  }
  console.log("PP-OCRv6 is up (official POST /ocr).");
  await verify();
  if ((process.env.PADDLEOCR_V6_WARMUP || "on").trim().toLowerCase() !== "off") {
    await warmup();
  }
}

async function verify() {
  const url = `${BASE}/ocr`;
  const res = await fetchProbe(url, 5000, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: "{}",
  });
  if (!res.status) {
    console.error(`PP-OCRv6 not reachable at ${url}: ${res.detail}`);
    process.exit(1);
  }
  console.log(`PP-OCRv6 OK — ${url} responded ${res.status}`);
  console.log("  Client contract: POST /ocr  { file: <base64>, fileType: 0|1, visualize?: false }");
}

/** 1×1 PNG — loads pipeline weights without a real document. */
const WARMUP_PNG_B64 =
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==";

async function warmup() {
  const url = `${BASE}/ocr`;
  console.log(`Warming PP-OCRv6 at ${url}…`);
  const started = Date.now();
  const res = await fetchProbe(url, 180_000, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      file: WARMUP_PNG_B64,
      fileType: 1,
      visualize: false,
    }),
  });
  if (!res.status) {
    console.error(`PP-OCRv6 warmup failed: ${res.detail || "no response"}`);
    process.exit(1);
  }
  if (res.status >= 500) {
    console.error(`PP-OCRv6 warmup HTTP ${res.status}`);
    process.exit(1);
  }
  console.log(`PP-OCRv6 warmup OK — HTTP ${res.status} in ${Date.now() - started}ms`);
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
  console.error("Usage: node deploy/scripts/paddleocr-v6-serve.mjs install|serve|stop|verify|warmup");
  process.exit(2);
}
