#!/usr/bin/env node
/**
 * llama-server for NuExtract3-GGUF (OpenAI-compatible).
 *
 * Flags follow official docs only:
 *   - https://huggingface.co/numind/NuExtract3-GGUF (vLLM low-memory: max-model-len 16384)
 *   - https://github.com/ggml-org/llama.cpp/blob/master/docs/multimodal.md
 *   - Qwen-VL accuracy floor: --image-min-tokens 1024 (llama.cpp)
 *
 * Usage: node deploy/scripts/llamacpp-nuextract3.mjs serve|stop|restart|verify|warmup
 */
import { spawn, spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { killListenerPort, parseEnvFile, resolveExecutable } from "./runtime-env.mjs";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const LLAMA_DIR = path.join(ROOT, "deploy/llamacpp");
const PATHS_FILE = path.join(LLAMA_DIR, "paths.local.env");
const LOG_DIR = path.join(LLAMA_DIR, "logs");
const WARMUP_MARKER = path.join(LOG_DIR, ".warmup-complete");

function findLlamaServerExe() {
  const probe = spawnSync("where.exe", ["llama-server"], { encoding: "utf8" });
  if (probe.status === 0) {
    const line = probe.stdout.split(/\r?\n/).find((l) => l.trim().endsWith("llama-server.exe"));
    if (line?.trim()) return line.trim();
  }
  return null;
}

function inferModelAlias(modelPath, explicitAlias) {
  if (explicitAlias?.trim()) {
    const alias = explicitAlias.trim();
    if (alias !== "nuextract3-q4_k_m") {
      console.warn(
        `warn: official local path uses alias nuextract3-q4_k_m; got ${alias}`,
      );
    }
    return alias;
  }
  const base = modelPath ? path.basename(modelPath, ".gguf") : "";
  if (base && !/Q4_K_M/i.test(base)) {
    console.warn(
      `warn: expected NuExtract3-Q4_K_M.gguf (official docs); got ${base}`,
    );
  }
  return "nuextract3-q4_k_m";
}

function resolvePaths() {
  const fileEnv = parseEnvFile(PATHS_FILE);
  const env = { ...fileEnv, ...process.env };
  const model = env.LLAMACPP_MODEL?.trim();
  const mmproj = env.LLAMACPP_MMPROJ?.trim();
  let exe = env.LLAMACPP_EXE?.trim() || findLlamaServerExe();
  const port = Number(env.LLAMACPP_PORT || 8081);
  const context = Number(env.LLAMACPP_CONTEXT || 16384);
  const gpuLayers = Number(env.LLAMACPP_GPU_LAYERS || 99);
  const device = env.LLAMACPP_DEVICE?.trim() || "";
  const parallel = Number(env.LLAMACPP_PARALLEL || 1);
  const modelAlias = inferModelAlias(model, env.LLAMACPP_MODEL_ALIAS);
  // Qwen-VL accuracy floor + Arc vision budget (llama.cpp). Do not lower min below 1024.
  const imageMinTokens = Number(env.LLAMACPP_IMAGE_MIN_TOKENS || 1024);
  const imageMaxTokens = Number(env.LLAMACPP_IMAGE_MAX_TOKENS || 1024);
  const ubatchSize = Number(env.LLAMACPP_UBATCH_SIZE || 1024);
  const mtmdBatchMaxTokens = Number(env.LLAMACPP_MTMD_BATCH_MAX_TOKENS || 1024);
  const flashAttn = (env.LLAMACPP_FLASH_ATTN || "on").trim().toLowerCase();
  if (env.LLAMACPP_WARMUP?.trim()) {
    process.env.LLAMACPP_WARMUP = env.LLAMACPP_WARMUP.trim();
  }
  const missing = [];
  if (!model || !fs.existsSync(model)) missing.push("LLAMACPP_MODEL");
  if (!mmproj || !fs.existsSync(mmproj)) missing.push("LLAMACPP_MMPROJ");
  if (!exe || !fs.existsSync(exe)) missing.push("LLAMACPP_EXE (or llama-server on PATH)");
  return {
    model,
    mmproj,
    exe,
    port,
    context,
    gpuLayers,
    device,
    parallel,
    modelAlias,
    imageMinTokens,
    imageMaxTokens,
    ubatchSize,
    mtmdBatchMaxTokens,
    flashAttn,
    missing,
  };
}

function buildServerEnv() {
  // Strip leftover CoopMat overrides so a stale user/system env cannot re-enable them.
  const env = { ...process.env };
  delete env.GGML_VK_DISABLE_COOPMAT;
  delete env.GGML_VK_DISABLE_COOPMAT2;
  delete env.LLAMACPP_STABILITY;
  return env;
}

function logLaunchFlags(paths) {
  const parts = [
    `-c ${paths.context}`,
    `-np ${paths.parallel}`,
    `-ngl ${paths.gpuLayers}`,
    `-fa ${paths.flashAttn}`,
    `-ub ${paths.ubatchSize}`,
    `--image-min-tokens ${paths.imageMinTokens}`,
    `--image-max-tokens ${paths.imageMaxTokens}`,
    `--mtmd-batch-max-tokens ${paths.mtmdBatchMaxTokens}`,
    "--mmproj-offload",
    "--jinja",
    "-rea off",
  ];
  if (paths.device) parts.push(`--device ${paths.device}`);
  console.log(`  ${parts.join(", ")}`);
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
  // Official multimodal serve + Qwen-VL vision budget + flash-attn.
  const args = [
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
    "-np",
    String(paths.parallel),
    "-ub",
    String(paths.ubatchSize),
    "-ngl",
    String(paths.gpuLayers),
    "-fa",
    paths.flashAttn,
    "--image-min-tokens",
    String(paths.imageMinTokens),
    "--image-max-tokens",
    String(paths.imageMaxTokens),
    "--mtmd-batch-max-tokens",
    String(paths.mtmdBatchMaxTokens),
    "--mmproj-offload",
    "-a",
    paths.modelAlias,
    "--jinja",
    "-rea",
    "off",
  ];
  if (paths.device) {
    args.push("--device", paths.device);
  }
  return args;
}

function stopServer(port) {
  try {
    fs.unlinkSync(WARMUP_MARKER);
  } catch {
    // marker may not exist
  }
  killListenerPort(port);
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

  console.log(`Starting llama-server on :${paths.port}...`);
  console.log(`  model:  ${paths.model}`);
  console.log(`  mmproj: ${paths.mmproj}`);
  console.log(`  logs:   ${LOG_DIR}`);
  logLaunchFlags(paths);

  const child = spawn(paths.exe, args, {
    cwd: LLAMA_DIR,
    detached: true,
    stdio: ["ignore", fs.openSync(outLog, "a"), fs.openSync(errLog, "a")],
    env: buildServerEnv(),
  });
  child.unref();

  const ready = await waitForServer(paths.port);
  if (!ready) {
    console.error("Timed out waiting for llama-server. Check logs in", LOG_DIR);
    process.exit(1);
  }
  console.log("llama-server is up.");
  await verify(paths.port);
  // Background warmup so `pnpm dev` / stack can continue to API+UI.
  // Force-sync via: pnpm llamacpp:warmup
  warmupRepodyVlm(paths.port, { force: false, background: true });
}

function warmupRepodyVlm(port, { force = false, background = false } = {}) {
  if ((process.env.LLAMACPP_WARMUP || "on").trim().toLowerCase() === "off") {
    console.log("\nSkipping NuExtract warmup (LLAMACPP_WARMUP=off).");
    return;
  }
  if (!force && fs.existsSync(WARMUP_MARKER)) {
    console.log("\nNuExtract warmup already completed for this server session — skipping.");
    return;
  }

  const uv = resolveExecutable("uv");
  const backendDir = path.join(ROOT, "backend");
  const warmupEnv = {
    ...process.env,
    AUDIT_INFERENCE_MODE: "llamacpp",
    AUDIT_LLAMACPP_BASE_URL: `http://127.0.0.1:${port}/v1`,
    AUDIT_REPODY_VLM_WARMUP_ON_START: "true",
  };

  console.log("\nPriming NuExtract (Facture.pdf, invoice + total-only schemas)...");
  if (background) {
    console.log("(background — stack continues; marker written by warmup_repody_vlm.py)");
    const child = spawn(uv, ["run", "python", "scripts/warmup_repody_vlm.py"], {
      cwd: backendDir,
      detached: true,
      stdio: "ignore",
      shell: false,
      env: warmupEnv,
    });
    child.unref();
    return;
  }

  const result = spawnSync(
    uv,
    ["run", "python", "scripts/warmup_repody_vlm.py"],
    {
      cwd: backendDir,
      encoding: "utf8",
      stdio: "inherit",
      shell: false,
      env: warmupEnv,
    },
  );
  if (result.status !== 0) {
    console.error("NuExtract warmup failed — first extraction may be slow.");
    process.exit(result.status ?? 1);
  }
  fs.mkdirSync(LOG_DIR, { recursive: true });
  fs.writeFileSync(WARMUP_MARKER, new Date().toISOString(), "utf8");
}

async function verify(port = Number(process.env.LLAMACPP_PORT || 8081)) {
  const paths = resolvePaths();
  const expectedAlias = paths.modelAlias;

  const models = await fetchJson(`http://127.0.0.1:${port}/v1/models`);
  const ids = (models.body?.data || []).map((m) => m.id);
  const meta = models.body?.data?.[0]?.meta;
  const nCtx = meta?.n_ctx;
  const caps = models.body?.models?.[0]?.capabilities || [];

  console.log("\n=== llama-server NuExtract3 check ===");
  console.log("expected:   ", expectedAlias);
  console.log("n_ctx:      ", nCtx);
  console.log("multimodal: ", caps.includes("multimodal"));
  console.log("models:     ", ids.join(", ") || "(none)");

  const failures = [];
  const parallel = Number(process.env.LLAMACPP_PARALLEL || paths?.parallel || 1);
  const minCtx = parallel > 1 ? Math.floor(16384 / parallel) : 16384;
  if (nCtx < minCtx) failures.push(`n_ctx ${nCtx} < ${minCtx} (parallel=${parallel})`);
  if (!caps.includes("multimodal")) failures.push("multimodal capability missing (mmproj not loaded?)");
  if (!ids.some((id) => /nuextract/i.test(id))) failures.push("NuExtract model not in /v1/models");
  if (!ids.includes(expectedAlias)) {
    failures.push(`served model ${ids.join(", ") || "(none)"} != expected ${expectedAlias}`);
  }

  if (failures.length) {
    console.error("\nNOT READY:");
    for (const f of failures) console.error(`  - ${f}`);
    process.exit(1);
  }
  console.log("\nREADY for Repody:");
  console.log(`  AUDIT_LLAMACPP_BASE_URL=http://host.docker.internal:${port}/v1`);
  console.log(`  AUDIT_LLAMACPP_SERVED_MODEL=${expectedAlias}`);
}

const cmd = process.argv[2] || "serve";
if (cmd === "serve") await serve();
else if (cmd === "stop") {
  const paths = resolvePaths();
  stopServer(paths.port);
  console.log(`Stopped llama-server on :${paths.port} (if it was running).`);
} else if (cmd === "restart") {
  const paths = resolvePaths();
  stopServer(paths.port);
  await new Promise((r) => setTimeout(r, 2000));
  await serve();
} else if (cmd === "verify") await verify();
else if (cmd === "warmup") {
  const paths = resolvePaths();
  warmupRepodyVlm(paths.port, { force: true });
} else {
  console.error("Usage: llamacpp-nuextract3.mjs serve|stop|restart|verify|warmup");
  process.exit(1);
}
