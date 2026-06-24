#!/usr/bin/env node
/**
 * Start llama-server for Surya OCR 2 (datalab-to/surya-ocr-2-gguf).
 *
 * Args mirror surya/inference/backends/llamacpp.py spawn defaults.
 *
 * Usage:
 *   node deploy/scripts/llamacpp-surya-ocr2.mjs serve
 *   node deploy/scripts/llamacpp-surya-ocr2.mjs verify
 *   node deploy/scripts/llamacpp-surya-ocr2.mjs stop
 *
 * Paths: deploy/llamacpp/surya-paths.local.env (copy from surya-paths.local.env.example)
 */
import { spawn, spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { killPort } from "./k8s-local-ports.mjs";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const LLAMA_DIR = path.join(ROOT, "deploy/llamacpp");
const PATHS_FILE = path.join(LLAMA_DIR, "surya-paths.local.env");
const LOG_DIR = path.join(LLAMA_DIR, "logs");

function parseEnvFile(filePath) {
  if (!fs.existsSync(filePath)) return {};
  const out = {};
  for (const line of fs.readFileSync(filePath, "utf8").split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;
    const idx = trimmed.indexOf("=");
    if (idx === -1) continue;
    out[trimmed.slice(0, idx).trim()] = trimmed.slice(idx + 1).trim();
  }
  return out;
}

function findLlamaServerExe() {
  const probe = spawnSync("where.exe", ["llama-server"], { encoding: "utf8" });
  if (probe.status === 0) {
    const line = probe.stdout.split(/\r?\n/).find((l) => l.trim().endsWith("llama-server.exe"));
    if (line?.trim()) return line.trim();
  }
  return null;
}

function resolvePaths() {
  const fileEnv = parseEnvFile(PATHS_FILE);
  const env = { ...fileEnv, ...process.env };
  const model = env.SURYA_LLAMACPP_MODEL?.trim();
  const mmproj = env.SURYA_LLAMACPP_MMPROJ?.trim();
  let exe = env.SURYA_LLAMACPP_EXE?.trim() || env.LLAMACPP_EXE?.trim() || findLlamaServerExe();
  const port = Number(env.SURYA_LLAMACPP_PORT || 8001);
  const parallel = Number(env.SURYA_LLAMACPP_PARALLEL || 8);
  const perSlot = Number(env.SURYA_LLAMACPP_CTX_PER_SLOT || 12288);
  const ctxSize = Number(
    env.SURYA_LLAMACPP_CTX_SIZE || Math.max(16384, parallel * perSlot),
  );
  const gpuLayers = Number(env.SURYA_LLAMACPP_GPU_LAYERS || env.LLAMACPP_GPU_LAYERS || 99);
  const alias = env.SURYA_LLAMACPP_ALIAS?.trim() || "datalab-to/surya-ocr-2";
  const device = env.SURYA_LLAMACPP_DEVICE?.trim() || env.LLAMACPP_DEVICE?.trim() || "";
  const extraArgs = (env.SURYA_LLAMACPP_EXTRA_ARGS || "").trim().split(/\s+/).filter(Boolean);
  const missing = [];
  if (!model || !fs.existsSync(model)) missing.push("SURYA_LLAMACPP_MODEL");
  if (!mmproj || !fs.existsSync(mmproj)) missing.push("SURYA_LLAMACPP_MMPROJ");
  if (!exe || !fs.existsSync(exe)) missing.push("SURYA_LLAMACPP_EXE (or llama-server on PATH)");
  return {
    model,
    mmproj,
    exe,
    port,
    parallel,
    perSlot,
    ctxSize,
    gpuLayers,
    alias,
    device,
    extraArgs,
    missing,
  };
}

async function fetchJson(url) {
  const res = await fetch(url);
  const text = await res.text();
  let body;
  try {
    body = JSON.parse(text);
  } catch {
    body = text;
  }
  return { ok: res.ok, status: res.status, body };
}

async function waitForServer(port, { timeoutMs = 300_000 } = {}) {
  const started = Date.now();
  while (Date.now() - started < timeoutMs) {
    try {
      const { ok } = await fetchJson(`http://127.0.0.1:${port}/v1/models`);
      if (ok) return true;
    } catch {
      // retry
    }
    await new Promise((r) => setTimeout(r, 3000));
  }
  return false;
}

function buildArgs(paths) {
  const args = [
    "-m",
    paths.model,
    "--mmproj",
    paths.mmproj,
    "-ngl",
    String(paths.gpuLayers),
    "--host",
    "0.0.0.0",
    "--port",
    String(paths.port),
    "--parallel",
    String(paths.parallel),
    "--ctx-size",
    String(paths.ctxSize),
    "--alias",
    paths.alias,
    "--jinja",
  ];
  if (paths.device) {
    args.push("--device", paths.device);
  }
  args.push(...paths.extraArgs);
  return args;
}

function collectVerifyFailures(modelsBody, paths) {
  const ids = (modelsBody?.data || []).map((m) => m.id);
  const meta = modelsBody?.data?.[0]?.meta;
  const nCtx = meta?.n_ctx;
  const caps = modelsBody?.models?.[0]?.capabilities || [];

  const failures = [];
  if (!caps.includes("multimodal")) failures.push("multimodal capability missing (mmproj not loaded?)");
  if (!ids.some((id) => /surya/i.test(id) || id === paths.alias)) {
    failures.push(`Surya model not in /v1/models (expected alias ${paths.alias})`);
  }
  if (nCtx != null && nCtx < paths.perSlot) {
    failures.push(
      `n_ctx ${nCtx} < ${paths.perSlot} per slot (datalab-to/surya SURYA_INFERENCE_CTX_PER_SLOT; server --ctx-size=${paths.ctxSize} for parallel=${paths.parallel})`,
    );
  }
  return { failures, ids, meta, caps, nCtx };
}

async function verify(paths = resolvePaths(), { exitOnFail = true } = {}) {
  const models = await fetchJson(`http://127.0.0.1:${paths.port}/v1/models`);
  const { failures, ids, caps, nCtx } = collectVerifyFailures(models.body, paths);

  console.log("\n=== llama-server Surya OCR 2 check ===");
  console.log("n_ctx:      ", nCtx);
  console.log("expected:   ", `${paths.perSlot} per slot (--ctx-size ${paths.ctxSize}, parallel=${paths.parallel})`);
  console.log("multimodal: ", caps.includes("multimodal"));
  console.log("models:     ", ids.join(", ") || "(none)");

  if (failures.length) {
    console.error("\nNOT READY:");
    for (const f of failures) console.error(`  - ${f}`);
    if (exitOnFail) process.exit(1);
    return { ok: false, failures };
  }

  console.log("\nREADY for Repody Surya benchmark:");
  console.log(`  AUDIT_SURYA_INFERENCE_BACKEND=llamacpp`);
  console.log(`  AUDIT_SURYA_INFERENCE_URL=http://host.docker.internal:${paths.port}/v1`);
  console.log(`  AUDIT_SURYA_INFERENCE_PARALLEL=${paths.parallel}`);
  return { ok: true, failures: [] };
}

async function startServer(paths) {
  fs.mkdirSync(LOG_DIR, { recursive: true });
  const outLog = path.join(LOG_DIR, "llama-server-surya.out.log");
  const errLog = path.join(LOG_DIR, "llama-server-surya.err.log");
  const args = buildArgs(paths);

  console.log(`Starting Surya llama-server on :${paths.port} (parallel=${paths.parallel}, ctx-size=${paths.ctxSize})...`);
  console.log(`  model:  ${paths.model}`);
  console.log(`  mmproj: ${paths.mmproj}`);
  console.log(`  logs:   ${LOG_DIR}`);

  const child = spawn(paths.exe, args, {
    cwd: LLAMA_DIR,
    detached: true,
    stdio: ["ignore", fs.openSync(outLog, "a"), fs.openSync(errLog, "a")],
  });
  child.unref();

  const ready = await waitForServer(paths.port);
  if (!ready) {
    console.error("Timed out waiting for Surya llama-server. Check logs in", LOG_DIR);
    process.exit(1);
  }
  console.log("Surya llama-server is up.");
}

async function serve() {
  const paths = resolvePaths();
  if (paths.missing.length) {
    console.error("Missing or invalid paths:", paths.missing.join(", "));
    console.error(
      `Copy ${path.join(LLAMA_DIR, "surya-paths.local.env.example")} → surya-paths.local.env`,
    );
    process.exit(1);
  }

  try {
    const ping = await fetchJson(`http://127.0.0.1:${paths.port}/v1/models`);
    if (ping.ok) {
      console.log(`Surya llama-server already listening on :${paths.port}`);
      const check = await verify(paths, { exitOnFail: false });
      if (check.ok) return;

      console.error(
        `\nRestarting :${paths.port} with ctx-size=${paths.ctxSize} (stale or misconfigured process).`,
      );
      killPort(paths.port);
      await new Promise((r) => setTimeout(r, 1500));
    }
  } catch {
    // not running
  }

  await startServer(paths);
  await verify(paths);
}

function stop() {
  const paths = resolvePaths();
  console.log(`Stopping listeners on :${paths.port}...`);
  killPort(paths.port);
}

const cmd = process.argv[2] || "serve";
if (cmd === "serve") await serve();
else if (cmd === "verify") await verify();
else if (cmd === "stop") stop();
else {
  console.error("Usage: llamacpp-surya-ocr2.mjs serve|verify|stop");
  process.exit(1);
}
