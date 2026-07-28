#!/usr/bin/env node
/**
 * PP-StructureV3 Basic Serving — official PaddleX layout-parsing pipeline.
 *
 * Docs:
 *   https://paddlepaddle.github.io/PaddleX/latest/en/pipeline_usage/tutorials/ocr_pipelines/PP-StructureV3.html
 *   https://www.paddleocr.ai/latest/en/version3.x/pipeline_usage/PP-StructureV3.html
 *
 * Official flow:
 *   paddlex --serve --pipeline PP-StructureV3 --host 0.0.0.0 --port 8870
 *   Client POST /layout-parsing  { file, fileType }
 *
 * Usage: node deploy/scripts/research/paddleocr-structure-v3-serve.mjs install|serve|stop|verify|warmup
 */
import { spawn, spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { fetchProbe, killListenerPort, resolveExecutable } from "../runtime-env.mjs";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../..");
const BACKEND = path.join(ROOT, "backend");
const LOG_DIR = path.join(ROOT, ".logs");
const PORT = Number(
  process.env.AUDIT_PADDLE_STRUCTURE_V3_PORT || process.env.PADDLE_STRUCTURE_V3_PORT || 8870,
);
const HOST = (
  process.env.AUDIT_PADDLE_STRUCTURE_V3_HOST ||
  process.env.PADDLE_STRUCTURE_V3_HOST ||
  "0.0.0.0"
).trim();
const DEVICE = (
  process.env.AUDIT_PADDLE_STRUCTURE_V3_DEVICE ||
  process.env.PADDLE_STRUCTURE_V3_DEVICE ||
  ""
).trim();
const PIPELINE = (
  process.env.AUDIT_PADDLE_STRUCTURE_V3_PIPELINE ||
  process.env.PADDLE_STRUCTURE_V3_PIPELINE ||
  "PP-StructureV3"
).trim();
const BASE = (
  process.env.AUDIT_PADDLE_STRUCTURE_V3_BASE_URL || `http://127.0.0.1:${PORT}`
).replace(/\/$/, "");

function uvBin() {
  return resolveExecutable("uv");
}

function buildServeArgs() {
  const args = [
    "run",
    "paddlex",
    "--serve",
    "--pipeline",
    PIPELINE,
    "--host",
    HOST,
    "--port",
    String(PORT),
  ];
  if (DEVICE) {
    args.push("--device", DEVICE);
  }
  return args;
}

async function waitForLayout({ timeoutMs = 900_000 } = {}) {
  const started = Date.now();
  const url = `${BASE}/layout-parsing`;
  while (Date.now() - started < timeoutMs) {
    const res = await fetchProbe(url, 3000, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: "{}",
    });
    if (res.status) return true;
    await new Promise((r) => setTimeout(r, 3000));
  }
  return false;
}

function install() {
  console.log("Ensuring PaddleX serving deps (fastapi/uvicorn) via uv…");
  // paddlex --install serving calls `python -m pip`, which fails in uv venvs.
  // Install the same serving stack with uv instead.
  const result = spawnSync(
    uvBin(),
    ["pip", "install", "fastapi>=0.110", "uvicorn>=0.30", "uvicorn[standard]>=0.30"],
    {
      cwd: BACKEND,
      stdio: "inherit",
      shell: false,
      env: { ...process.env },
    },
  );
  if (result.status !== 0) {
    process.exit(result.status || 1);
  }
  console.log("Serving deps ready.");
}

async function serve() {
  const already = await fetchProbe(`${BASE}/layout-parsing`, 2000, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: "{}",
  });
  if (already.status) {
    console.log(`PP-StructureV3 already listening on ${BASE}`);
    await verify();
    return;
  }

  fs.mkdirSync(LOG_DIR, { recursive: true });
  const outLog = path.join(LOG_DIR, "paddleocr-structure-v3.out.log");
  const errLog = path.join(LOG_DIR, "paddleocr-structure-v3.err.log");
  const args = buildServeArgs();

  console.log(`Starting PP-StructureV3 Basic Serving on ${HOST}:${PORT} …`);
  console.log(`  pipeline: ${PIPELINE}`);
  if (DEVICE) console.log(`  device:   ${DEVICE}`);
  console.log(`  logs:     ${LOG_DIR}`);
  console.log(`  endpoint: POST ${BASE}/layout-parsing`);

  const child = spawn(uvBin(), args, {
    cwd: BACKEND,
    detached: true,
    stdio: ["ignore", fs.openSync(outLog, "a"), fs.openSync(errLog, "a")],
    shell: false,
    env: { ...process.env, PYTHONUNBUFFERED: "1" },
  });
  child.unref();

  const ready = await waitForLayout();
  if (!ready) {
    console.error(`Timed out waiting for PP-StructureV3 at ${BASE}/layout-parsing — check ${errLog}`);
    console.error("If serve fails, run: pnpm paddleocr:structure-v3:install");
    process.exit(1);
  }
  console.log("PP-StructureV3 is up (official POST /layout-parsing).");
  await verify();
  if ((process.env.PADDLE_STRUCTURE_V3_WARMUP || "on").trim().toLowerCase() !== "off") {
    await warmup();
  }
}

async function verify() {
  const url = `${BASE}/layout-parsing`;
  const res = await fetchProbe(url, 5000, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: "{}",
  });
  if (!res.status) {
    console.error(`PP-StructureV3 not reachable at ${url}: ${res.detail}`);
    process.exit(1);
  }
  console.log(`PP-StructureV3 OK — ${url} responded ${res.status}`);
  console.log(
    "  Client contract: POST /layout-parsing  { file: <base64>, fileType: 0|1, visualize?: false }",
  );
}

const WARMUP_PNG_B64 =
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==";

async function warmup() {
  const url = `${BASE}/layout-parsing`;
  console.log(`Warming PP-StructureV3 at ${url}…`);
  const started = Date.now();
  const res = await fetchProbe(url, 300_000, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      file: WARMUP_PNG_B64,
      fileType: 1,
      visualize: false,
    }),
  });
  if (!res.status) {
    console.error(`PP-StructureV3 warmup failed: ${res.detail || "no response"}`);
    process.exit(1);
  }
  if (res.status >= 500) {
    console.error(`PP-StructureV3 warmup HTTP ${res.status}`);
    process.exit(1);
  }
  console.log(`PP-StructureV3 warmup OK — HTTP ${res.status} in ${Date.now() - started}ms`);
}

function stop() {
  killListenerPort(PORT);
  console.log(`Stopped PP-StructureV3 on :${PORT} (if it was running).`);
}

const cmd = process.argv[2] || "serve";
if (cmd === "install") install();
else if (cmd === "serve") void serve();
else if (cmd === "stop") stop();
else if (cmd === "verify") void verify();
else if (cmd === "warmup") void warmup();
else {
  console.error(
    "Usage: node deploy/scripts/research/paddleocr-structure-v3-serve.mjs install|serve|stop|verify|warmup",
  );
  process.exit(2);
}
