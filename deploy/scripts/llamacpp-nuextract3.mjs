#!/usr/bin/env node
/**
 * Start llama-server for NuExtract3 Repody (Q4_K_M default + mmproj + 16k, Vulkan by default).
 *
 * Usage:
 *   node deploy/scripts/llamacpp-nuextract3.mjs serve|stop|restart|verify
 *
 * Paths: deploy/llamacpp/paths.local.env (copy from paths.local.env.example)
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
  if (explicitAlias?.trim()) return explicitAlias.trim();
  const base = modelPath ? path.basename(modelPath, ".gguf") : "";
  if (/Q4_K_M/i.test(base)) return "nuextract3-q4_k_m";
  if (/Q8_0/i.test(base)) return "nuextract3-q8_0";
  return "nuextract3-q4_k_m";
}

function resolveProfileDefaults(isVulkan, env) {
  const profile = (env.LLAMACPP_PROFILE || "speed").trim().toLowerCase();
  if (profile === "stability") {
    return {
      profile,
      flashAttn: "off",
      cacheTypeK: "q8_0",
      cacheTypeV: "f16",
      ubatch: 1024,
      mtmdBatchMaxTokens: 1024,
      vkMaxNodesPerSubmit: isVulkan ? 1 : 0,
      cachePrompt: false,
    };
  }
  // speed (default): Arc Vulkan tuned — see deploy/llamacpp/README.md (~7–13s warm)
  return {
    profile,
    flashAttn: "on",
    cacheTypeK: "q8_0",
    cacheTypeV: "q8_0",
    ubatch: 1024,
    mtmdBatchMaxTokens: 1024,
    vkMaxNodesPerSubmit: isVulkan ? 1 : 0,
    cachePrompt: true,
  };
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
  const device = env.LLAMACPP_DEVICE?.trim() || "Vulkan0";
  const isVulkan = device.toLowerCase().startsWith("vulkan");
  const parallel = Number(env.LLAMACPP_PARALLEL || 1);
  const imageMinTokens = Number(env.LLAMACPP_IMAGE_MIN_TOKENS || 1024);
  const imageMaxTokens = env.LLAMACPP_IMAGE_MAX_TOKENS?.trim()
    ? Number(env.LLAMACPP_IMAGE_MAX_TOKENS)
    : null;
  const cacheRamMiB = Number(env.LLAMACPP_CACHE_RAM_MIB || 2048);
  const fit = (env.LLAMACPP_FIT || "on").trim().toLowerCase();
  const profileDefaults = resolveProfileDefaults(isVulkan, env);
  const flashAttn = (env.LLAMACPP_FLASH_ATTN || profileDefaults.flashAttn).trim().toLowerCase();
  const cacheTypeK = (env.LLAMACPP_CACHE_TYPE_K || profileDefaults.cacheTypeK).trim().toLowerCase();
  let cacheTypeV = (env.LLAMACPP_CACHE_TYPE_V || profileDefaults.cacheTypeV).trim().toLowerCase();
  if (cacheTypeV !== "f16" && flashAttn === "off") {
    cacheTypeV = "f16";
  }
  const ubatch = Number(env.LLAMACPP_UBATCH || profileDefaults.ubatch);
  const mtmdBatchMaxTokens = Number(
    env.LLAMACPP_MTMD_BATCH_MAX_TOKENS || profileDefaults.mtmdBatchMaxTokens,
  );
  const vkMaxNodesPerSubmit = env.LLAMACPP_VK_MAX_NODES_PER_SUBMIT?.trim()
    ? Number(env.LLAMACPP_VK_MAX_NODES_PER_SUBMIT)
    : profileDefaults.vkMaxNodesPerSubmit;
  const vkDisableCoopmat = (env.LLAMACPP_VK_DISABLE_COOPMAT || "").trim() === "1";
  const cachePrompt = env.LLAMACPP_CACHE_PROMPT
    ? env.LLAMACPP_CACHE_PROMPT.trim().toLowerCase() !== "off"
    : profileDefaults.cachePrompt;
  const modelAlias = inferModelAlias(model, env.LLAMACPP_MODEL_ALIAS);
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
    isVulkan,
    parallel,
    imageMinTokens,
    imageMaxTokens,
    cacheRamMiB,
    fit,
    profile: profileDefaults.profile,
    flashAttn,
    cacheTypeK,
    cacheTypeV,
    ubatch,
    mtmdBatchMaxTokens,
    vkMaxNodesPerSubmit,
    vkDisableCoopmat,
    cachePrompt,
    modelAlias,
    missing,
  };
}

function buildChildEnv(paths) {
  const childEnv = { ...process.env };
  if (paths.isVulkan && paths.vkMaxNodesPerSubmit > 0) {
    childEnv.GGML_VK_MAX_NODES_PER_SUBMIT = String(paths.vkMaxNodesPerSubmit);
  }
  if (paths.isVulkan && paths.vkDisableCoopmat) {
    childEnv.GGML_VK_DISABLE_COOPMAT = "1";
  }
  return childEnv;
}

function logStabilityProfile(paths) {
  const parts = [
    `profile=${paths.profile}`,
    `-fa ${paths.flashAttn}`,
    `-ctk ${paths.cacheTypeK} -ctv ${paths.cacheTypeV}`,
    `-ub ${paths.ubatch}`,
    `--mtmd-batch-max-tokens ${paths.mtmdBatchMaxTokens}`,
  ];
  if (paths.isVulkan && paths.vkMaxNodesPerSubmit > 0) {
    parts.push(`GGML_VK_MAX_NODES_PER_SUBMIT=${paths.vkMaxNodesPerSubmit}`);
  }
  if (!paths.cachePrompt) parts.push("--no-cache-prompt");
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
    "-fa",
    paths.flashAttn === "on" ? "on" : "off",
    "-ctk",
    paths.cacheTypeK,
    "-ctv",
    paths.cacheTypeV,
    "-ngl",
    String(paths.gpuLayers),
    "--device",
    paths.device,
    "--mmproj-offload",
    "--image-min-tokens",
    String(paths.imageMinTokens),
    "--mtmd-batch-max-tokens",
    String(paths.mtmdBatchMaxTokens),
    "-ub",
    String(paths.ubatch),
    "-a",
    paths.modelAlias,
    "--jinja",
    "-rea",
    "off",
  ];
  if (paths.imageMaxTokens != null && Number.isFinite(paths.imageMaxTokens)) {
    args.push("--image-max-tokens", String(paths.imageMaxTokens));
  }
  if (paths.fit === "off") {
    args.push("--fit", "off");
  }
  if (!paths.cachePrompt) {
    args.push("--no-cache-prompt");
  }
  if (Number.isFinite(paths.cacheRamMiB) && paths.cacheRamMiB >= 0) {
    args.push("--cache-ram", String(paths.cacheRamMiB));
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

  console.log(`Starting llama-server on :${paths.port} (${paths.device}, -np ${paths.parallel})...`);
  if (paths.parallel > 1) {
    console.log(
      `  hint: set admissionMaxExtractInflight >= ${paths.parallel} and scale worker-extract to match.`,
    );
  }
  console.log(`  model:  ${paths.model}`);
  console.log(`  mmproj: ${paths.mmproj}`);
  console.log(`  logs:   ${LOG_DIR}`);
  logStabilityProfile(paths);

  const child = spawn(paths.exe, args, {
    cwd: LLAMA_DIR,
    detached: true,
    stdio: ["ignore", fs.openSync(outLog, "a"), fs.openSync(errLog, "a")],
    env: buildChildEnv(paths),
  });
  child.unref();

  const ready = await waitForServer(paths.port);
  if (!ready) {
    console.error("Timed out waiting for llama-server. Check logs in", LOG_DIR);
    process.exit(1);
  }
  console.log("llama-server is up.");
  await verify(paths.port);
  warmupRepodyVlm(paths.port, { force: false });
}

function warmupRepodyVlm(port, { force = false } = {}) {
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
    AUDIT_INFERENCE_MODE: "vllm",
    AUDIT_VLLM_BASE_URL: `http://127.0.0.1:${port}/v1`,
    AUDIT_REPODY_VLM_WARMUP_ON_START: "true",
  };

  console.log("\nPriming NuExtract prompt cache (Facture.pdf, invoice + total-only schemas)...");
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
  console.log(`  AUDIT_VLLM_BASE_URL=http://host.docker.internal:${port}/v1`);
  console.log(`  AUDIT_VLLM_SERVED_MODEL=${expectedAlias}`);
}

async function serveWithWarmup(paths) {
  await verify(paths.port);
  warmupRepodyVlm(paths.port, { force: true });
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
