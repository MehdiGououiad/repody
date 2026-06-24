#!/usr/bin/env node
/**
 * Start llama-server for NuExtract3 Repody (Q8 + mmproj + 16k, Vulkan by default).
 *
 * Usage:
 *   node deploy/scripts/llamacpp-nuextract3.mjs serve
 *   node deploy/scripts/llamacpp-nuextract3.mjs verify
 *
 * Paths: deploy/llamacpp/paths.local.env (copy from paths.local.env.example)
 */
import { spawn, spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const LLAMA_DIR = path.join(ROOT, "deploy/llamacpp");
const PATHS_FILE = path.join(LLAMA_DIR, "paths.local.env");
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
  const model = env.LLAMACPP_MODEL?.trim();
  const mmproj = env.LLAMACPP_MMPROJ?.trim();
  let exe = env.LLAMACPP_EXE?.trim() || findLlamaServerExe();
  const port = Number(env.LLAMACPP_PORT || 8000);
  const context = Number(env.LLAMACPP_CONTEXT || 16384);
  const gpuLayers = Number(env.LLAMACPP_GPU_LAYERS || 99);
  const device = env.LLAMACPP_DEVICE?.trim() || "Vulkan0";
  const missing = [];
  if (!model || !fs.existsSync(model)) missing.push("LLAMACPP_MODEL");
  if (!mmproj || !fs.existsSync(mmproj)) missing.push("LLAMACPP_MMPROJ");
  if (!exe || !fs.existsSync(exe)) missing.push("LLAMACPP_EXE (or llama-server on PATH)");
  return { model, mmproj, exe, port, context, gpuLayers, device, missing };
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
  return [
    "-m",
    paths.model,
    "--mmproj",
    paths.mmproj,
    "--host",
    "0.0.0.0",
    "--port",
    String(paths.port),
    "-c",
    String(paths.context),
    "-fa",
    "on",
    "-ctk",
    "q8_0",
    "-ctv",
    "q8_0",
    "-ngl",
    String(paths.gpuLayers),
    "--device",
    paths.device,
    "--mmproj-offload",
    "-ub",
    "256",
    "-a",
    "nuextract3-q8_0",
    "--jinja",
    "-rea",
    "off",
  ];
}

async function serve() {
  const paths = resolvePaths();
  if (paths.missing.length) {
    console.error("Missing or invalid paths:", paths.missing.join(", "));
    console.error(`Copy ${path.join(LLAMA_DIR, "paths.local.env.example")} → paths.local.env`);
    process.exit(1);
  }

  try {
    const ping = await fetchJson(`http://127.0.0.1:${paths.port}/v1/models`);
    if (ping.ok) {
      console.log(`llama-server already listening on :${paths.port}`);
      await verify(paths.port);
      return;
    }
  } catch {
    // not running
  }

  fs.mkdirSync(LOG_DIR, { recursive: true });
  const outLog = path.join(LOG_DIR, "llama-server.out.log");
  const errLog = path.join(LOG_DIR, "llama-server.err.log");
  const args = buildArgs(paths);

  console.log(`Starting llama-server on :${paths.port} (${paths.device})...`);
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
    console.error("Timed out waiting for llama-server. Check logs in", LOG_DIR);
    process.exit(1);
  }
  console.log("llama-server is up.");
  await verify(paths.port);
}

async function verify(port = Number(process.env.LLAMACPP_PORT || 8000)) {
  const models = await fetchJson(`http://127.0.0.1:${port}/v1/models`);
  const ids = (models.body?.data || []).map((m) => m.id);
  const meta = models.body?.data?.[0]?.meta;
  const nCtx = meta?.n_ctx;
  const caps = models.body?.models?.[0]?.capabilities || [];

  console.log("\n=== llama-server NuExtract3 check ===");
  console.log("n_ctx:      ", nCtx);
  console.log("multimodal: ", caps.includes("multimodal"));
  console.log("models:     ", ids.join(", ") || "(none)");

  const failures = [];
  if (nCtx < 16384) failures.push(`n_ctx ${nCtx} < 16384`);
  if (!caps.includes("multimodal")) failures.push("multimodal capability missing (mmproj not loaded?)");
  if (!ids.some((id) => /nuextract/i.test(id))) failures.push("NuExtract model not in /v1/models");

  if (failures.length) {
    console.error("\nNOT READY:");
    for (const f of failures) console.error(`  - ${f}`);
    process.exit(1);
  }
  console.log("\nREADY for Repody:");
  console.log(`  REPODY_VLLM_BASE_URL=http://host.docker.internal:${port}/v1`);
  console.log(`  REPODY_VLLM_SERVED_MODEL=${ids[0]}`);
}

const cmd = process.argv[2] || "serve";
if (cmd === "serve") await serve();
else if (cmd === "verify") await verify();
else {
  console.error("Usage: llamacpp-nuextract3.mjs serve|verify");
  process.exit(1);
}
