#!/usr/bin/env node
/**
 * Host llama-server lifecycle for the Repody models (OpenAI-compatible, detached).
 *
 *   node deploy/scripts/llama-serve.mjs <model> serve|stop|restart|verify|warmup|download
 *
 * Models (each reads deploy/<dir>/paths.local.env, overridable by process env):
 *   nuextract  NuExtract3 GGUF + mmproj     :8081  LLAMACPP_*   https://huggingface.co/numind/NuExtract3-GGUF
 *   qwen35     Qwen3.5-4B (text -> JSON)    :8084  QWEN35_*     https://huggingface.co/unsloth/Qwen3.5-4B-GGUF
 *   glmocr     GLM-OCR (F16 > Q8_0 for OCR) :8083  GLMOCR_*     https://huggingface.co/ggml-org/GLM-OCR-GGUF
 *
 * Flags follow the official model cards and llama.cpp docs/multimodal.md.
 */
import { spawn, spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import {
  fetchJson,
  findExecutable,
  killListenerPort,
  parseEnvFile,
  ROOT,
  resolveExecutable,
  waitForLlamaServer,
  waitForPortRelease,
} from "./runtime-env.mjs";

/** 1×1 PNG - primes the vision path without a real document. */
const WARMUP_PNG_B64 =
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==";

const NUEXTRACT_MARKER = path.join(ROOT, "deploy/llamacpp/logs/.warmup-complete");

function nuextractAlias(modelPath, explicitAlias) {
  // Local default is Q8_0 (deep-bench winner); HF "small local" pack is Q4_K_M.
  if (explicitAlias) return explicitAlias;
  const base = modelPath ? path.basename(modelPath, ".gguf") : "";
  if (/Q8_0/i.test(base)) return "nuextract3-q8_0";
  if (/Q6_K/i.test(base)) return "nuextract3-q6_k";
  if (/Q5_K_M/i.test(base)) return "nuextract3-q5_k_m";
  if (/Q4_K_M/i.test(base)) return "nuextract3-q4_k_m";
  return "nuextract3-q8_0";
}

/** Newer LM Studio / llama.cpp builds dropped --mtmd-batch-max-tokens; `0` force-disables. */
function mtmdBatchArgs(exe, raw) {
  if (raw) {
    const n = Number(raw);
    return Number.isFinite(n) && n > 0 ? ["--mtmd-batch-max-tokens", String(n)] : [];
  }
  if (!exe || !fs.existsSync(exe)) return [];
  const help = spawnSync(exe, ["--help"], { encoding: "utf8", windowsHide: true });
  return `${help.stdout || ""}\n${help.stderr || ""}`.includes("--mtmd-batch-max-tokens")
    ? ["--mtmd-batch-max-tokens", "1024"]
    : [];
}

/**
 * Per-model config. `get(key, fallback)` reads `<prefix>_<key>`.
 * `source` returns the model args (-m / -hf); `flags` the model-specific tuning.
 */
const MODELS = {
  nuextract: {
    label: "NuExtract3",
    dir: "deploy/llamacpp",
    prefix: "LLAMACPP",
    logName: "llama-server",
    port: 8081,
    context: 16384,
    hfRepo: "numind/NuExtract3-GGUF",
    readyTimeoutMs: 300_000,
    // Local GGUF + mmproj only (no -hf mode).
    source: (get) => ({
      model: get("MODEL"),
      mmproj: get("MMPROJ"),
      useHf: false,
      alias: nuextractAlias(get("MODEL"), get("MODEL_ALIAS")),
      requireMmproj: true,
    }),
    // Qwen-VL accuracy floor: --image-min-tokens 1024 (do not lower). -rea off: no thinking.
    flags: (get, exe) => [
      ...["-ub", get("UBATCH_SIZE", "1024"), "-fa", get("FLASH_ATTN", "on").toLowerCase()],
      ...["--image-min-tokens", get("IMAGE_MIN_TOKENS", "1024")],
      ...["--image-max-tokens", get("IMAGE_MAX_TOKENS", "1024")],
      ...mtmdBatchArgs(exe, get("MTMD_BATCH_MAX_TOKENS")),
      ...["--mmproj-offload", "--jinja", "-rea", "off"],
    ],
    // Strip leftover CoopMat overrides so a stale user/system env cannot re-enable them.
    serverEnv: (env) => {
      delete env.GGML_VK_DISABLE_COOPMAT;
      delete env.GGML_VK_DISABLE_COOPMAT2;
      delete env.LLAMACPP_STABILITY;
      return env;
    },
    verify: ({ body, alias, get }) => {
      const failures = [];
      const ids = (body?.data || []).map((m) => m.id);
      const nCtx = body?.data?.[0]?.meta?.n_ctx;
      const caps = body?.models?.[0]?.capabilities || [];
      const parallel = Number(get("PARALLEL", "1"));
      const minCtx = parallel > 1 ? Math.floor(16384 / parallel) : 16384;
      console.log(`  n_ctx: ${nCtx}  multimodal: ${caps.includes("multimodal")}`);
      if (!(nCtx >= minCtx)) failures.push(`n_ctx ${nCtx} < ${minCtx} (parallel=${parallel})`);
      if (!caps.includes("multimodal"))
        failures.push("multimodal capability missing (mmproj not loaded?)");
      if (!ids.includes(alias)) failures.push(`served model != expected ${alias}`);
      return failures;
    },
    // Opt-in (LLAMACPP_WARMUP=on) on serve, and in the background so the stack continues.
    warmupOnServe: (get) => get("WARMUP", "off").toLowerCase() === "on" && "background",
    warmup: ({ port, background, force }) => nuextractWarmup(port, { background, force }),
    onStop: () => fs.rmSync(NUEXTRACT_MARKER, { force: true }),
    envHint: (port, alias) => [
      `AUDIT_LLAMACPP_BASE_URL=http://host.docker.internal:${port}/v1`,
      `AUDIT_LLAMACPP_SERVED_MODEL=${alias}`,
    ],
  },
  qwen35: {
    label: "Qwen3.5-4B",
    dir: "deploy/qwen35",
    prefix: "QWEN35",
    logName: "qwen35",
    port: 8084,
    context: 8192,
    hfRepo: "unsloth/Qwen3.5-4B-GGUF",
    source: (get) => ({
      model: get("MODEL"),
      useHf: isTrue(get("USE_HF")) || !get("MODEL"),
      hfArgs: (repo) => ["-hf", repo, ...(get("HF_FILE") ? ["--hf-file", get("HF_FILE")] : [])],
      alias: get("MODEL_ALIAS", "Qwen3.5-4B"),
    }),
    // Qwen3.5 defaults to thinking; disable for JSON extraction.
    flags: () => ["--temp", "0.0", "--jinja", "--reasoning", "off"],
    warmupOnServe: (get) => get("WARMUP", "on").toLowerCase() !== "off",
    warmup: ({ port, alias }) =>
      chatWarmup("Qwen3.5-4B", port, alias, [
        { role: "system", content: "Reply with a single JSON object only." },
        { role: "user", content: 'Return {"ok":true}' },
      ]),
    envHint: (port) => [`AUDIT_QWEN35_BASE_URL=http://127.0.0.1:${port}/v1`],
  },
  glmocr: {
    label: "GLM-OCR",
    dir: "deploy/glmocr",
    prefix: "GLMOCR",
    logName: "glmocr",
    port: 8083,
    // Region crops rarely need 8192; 4096 saves VRAM when sharing iGPU with NuExtract.
    context: 4096,
    hfRepo: "ggml-org/GLM-OCR-GGUF",
    source: (get) => ({
      model: get("MODEL"),
      mmproj: get("MMPROJ"),
      useHf: isTrue(get("USE_HF")) || !get("MODEL"),
      // Official ggml blog: llama-server -hf ggml-org/GLM-OCR-GGUF:F16
      hfArgs: (repo) => ["-hf", `${repo}:${get("HF_QUANT", "F16")}`],
      alias: get("MODEL_ALIAS", "GLM-OCR"),
    }),
    // Official zai-org SDK page_loader: temperature 0.0, top_k 1 (greedy OCR).
    flags: (get, exe) => [
      ...["-ub", get("UBATCH_SIZE", "512"), "-fa", get("FLASH_ATTN", "on").toLowerCase()],
      ...["--image-max-tokens", get("IMAGE_MAX_TOKENS", "1024")],
      ...["--temp", "0.0", "--top-k", "1", "--top-p", "0.00001", "--repeat-penalty", "1.1"],
      "--jinja",
      ...mtmdBatchArgs(exe, get("MTMD_BATCH_MAX_TOKENS")),
    ],
    warmupOnServe: (get) => get("WARMUP", "off").toLowerCase() === "on",
    warmup: ({ port, alias }) =>
      chatWarmup("GLM-OCR", port, alias, [
        {
          role: "user",
          content: [
            { type: "image_url", image_url: { url: `data:image/png;base64,${WARMUP_PNG_B64}` } },
            { type: "text", text: "Text Recognition:" },
          ],
        },
      ]),
    envHint: (port) => [
      `AUDIT_GLM_OCR_BASE_URL=http://127.0.0.1:${port}/v1`,
      `Compose workers: http://host.docker.internal:${port}/v1`,
    ],
  },
};

function isTrue(value) {
  return value.toLowerCase() === "true" || value === "1";
}

function resolve(spec) {
  const dir = path.join(ROOT, spec.dir);
  const env = { ...parseEnvFile(path.join(dir, "paths.local.env")), ...process.env };
  const get = (key, fallback = "") => env[`${spec.prefix}_${key}`]?.trim() || fallback;
  const exe = get("EXE") || env.LLAMACPP_EXE?.trim() || findExecutable("llama-server");
  const src = spec.source(get);
  const port = Number(get("PORT", String(spec.port)));
  const missing = [];
  if (!exe || !fs.existsSync(exe)) missing.push(`${spec.prefix}_EXE (or llama-server on PATH)`);
  if (!src.useHf) {
    if (!src.model || !fs.existsSync(src.model)) missing.push(`${spec.prefix}_MODEL`);
    if ((src.requireMmproj || src.mmproj) && !(src.mmproj && fs.existsSync(src.mmproj))) {
      missing.push(`${spec.prefix}_MMPROJ`);
    }
  }
  return { dir, logDir: path.join(dir, "logs"), get, exe, port, src, missing };
}

function buildArgs(spec, cfg) {
  const { get, src } = cfg;
  const args = src.useHf
    ? src.hfArgs(spec.hfRepo)
    : ["-m", src.model, ...(src.mmproj ? ["--mmproj", src.mmproj] : [])];
  args.push(
    ...["--host", "0.0.0.0", "--port", String(cfg.port)],
    ...["-c", get("CONTEXT", String(spec.context)), "-np", get("PARALLEL", "1")],
    ...["-ngl", get("GPU_LAYERS", "99"), "-a", src.alias],
    ...spec.flags(get, cfg.exe)
  );
  if (get("DEVICE")) args.push("--device", get("DEVICE"));
  return args;
}

async function chatWarmup(label, port, model, messages) {
  const url = `http://127.0.0.1:${port}/v1/chat/completions`;
  console.log(`Warming ${label} at ${url} (model=${model})…`);
  const started = Date.now();
  try {
    const res = await fetch(url, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ model, temperature: 0, max_tokens: 16, messages }),
      signal: AbortSignal.timeout(180_000),
    });
    const text = await res.text();
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${text.slice(0, 400)}`);
  } catch (err) {
    console.error(`${label} warmup failed: ${err instanceof Error ? err.message : err}`);
    process.exit(1);
  }
  console.log(`${label} warmup OK — ${Date.now() - started}ms`);
}

/** Facture.pdf through the real VLM adapter; the script writes the marker on success. */
function nuextractWarmup(port, { background = false, force = false } = {}) {
  if (!force && fs.existsSync(NUEXTRACT_MARKER)) {
    console.log("NuExtract warmup already completed for this server session — skipping.");
    return;
  }
  const uvArgs = ["run", "python", "scripts/warmup_repody_vlm.py"];
  const opts = {
    cwd: path.join(ROOT, "backend"),
    shell: false,
    env: {
      ...process.env,
      AUDIT_INFERENCE_MODE: "llamacpp",
      AUDIT_LLAMACPP_BASE_URL: `http://127.0.0.1:${port}/v1`,
      AUDIT_REPODY_VLM_WARMUP_ON_START: "true",
    },
  };
  console.log("\nPriming NuExtract (Facture.pdf, invoice + total-only schemas)...");
  if (background) {
    console.log("(background — stack continues; marker written by warmup_repody_vlm.py)");
    spawn(resolveExecutable("uv"), uvArgs, { ...opts, detached: true, stdio: "ignore" }).unref();
    return;
  }
  const result = spawnSync(resolveExecutable("uv"), uvArgs, { ...opts, stdio: "inherit" });
  if (result.status !== 0) {
    console.error("NuExtract warmup failed — first extraction may be slow.");
    process.exit(result.status ?? 1);
  }
  fs.mkdirSync(path.dirname(NUEXTRACT_MARKER), { recursive: true });
  fs.writeFileSync(NUEXTRACT_MARKER, new Date().toISOString(), "utf8");
}

async function verify(spec, cfg) {
  const url = `http://127.0.0.1:${cfg.port}/v1/models`;
  let res;
  try {
    res = await fetchJson(url);
  } catch (err) {
    console.error(`${spec.label} not reachable at ${url}: ${err}`);
    process.exit(1);
  }
  if (!res.ok) {
    console.error(`${spec.label} not ready at ${url}: HTTP ${res.status}`);
    process.exit(1);
  }
  const ids = Array.isArray(res.body?.data) ? res.body.data.map((m) => m.id).filter(Boolean) : [];
  console.log(`${spec.label} OK — ${url}`);
  console.log(`  models: ${ids.join(", ") || "(none)"}`);
  const failures = spec.verify?.({ body: res.body, alias: cfg.src.alias, get: cfg.get }) ?? [];
  if (failures.length) {
    console.error("\nNOT READY:");
    for (const f of failures) console.error(`  - ${f}`);
    process.exit(1);
  }
}

async function serve(spec, cfg) {
  if (cfg.missing.length) {
    console.error("Missing or invalid paths:", cfg.missing.join(", "));
    console.error(`Copy ${path.join(cfg.dir, "paths.local.env.example")} → paths.local.env`);
    process.exit(1);
  }
  if ((await fetchJson(`http://127.0.0.1:${cfg.port}/v1/models`).catch(() => ({}))).ok) {
    console.log(`${spec.label} llama-server already listening on :${cfg.port}`);
    await verify(spec, cfg);
    return;
  }

  fs.mkdirSync(cfg.logDir, { recursive: true });
  const args = buildArgs(spec, cfg);
  console.log(`Starting ${spec.label} on :${cfg.port}...`);
  console.log(`  args: ${args.join(" ")}`);
  console.log(`  logs: ${cfg.logDir}`);
  spawn(cfg.exe, args, {
    cwd: cfg.dir,
    detached: true,
    stdio: [
      "ignore",
      fs.openSync(path.join(cfg.logDir, `${spec.logName}.out.log`), "a"),
      fs.openSync(path.join(cfg.logDir, `${spec.logName}.err.log`), "a"),
    ],
    env: spec.serverEnv ? spec.serverEnv({ ...process.env }) : process.env,
  }).unref();

  if (!(await waitForLlamaServer(cfg.port, { timeoutMs: spec.readyTimeoutMs }))) {
    console.error(`Timed out waiting for ${spec.label} llama-server. Check logs in`, cfg.logDir);
    process.exit(1);
  }
  console.log(`${spec.label} llama-server is up.`);
  await verify(spec, cfg);
  const warm = spec.warmupOnServe(cfg.get);
  if (warm) {
    await spec.warmup({ port: cfg.port, alias: cfg.src.alias, background: warm === "background" });
  } else {
    console.log(`(warmup skipped — ${spec.prefix}_WARMUP=on or: llama-serve.mjs <model> warmup)`);
  }
  for (const line of spec.envHint(cfg.port, cfg.src.alias)) console.log(`  ${line}`);
}

function stop(spec, cfg) {
  spec.onStop?.();
  killListenerPort(cfg.port);
  console.log(`Stopped ${spec.label} on :${cfg.port} (if it was running).`);
}

function download(spec, cfg) {
  const dest = path.join(cfg.dir, "models");
  fs.mkdirSync(dest, { recursive: true });
  console.log(`Downloading ${spec.hfRepo} into ${dest} …`);
  const result = spawnSync(
    resolveExecutable("hf"),
    ["download", spec.hfRepo, "--local-dir", dest],
    {
      stdio: "inherit",
      shell: false,
    }
  );
  if (result.status !== 0) {
    console.error(
      "hf download failed. Install the Hugging Face CLI (`pip install huggingface_hub`)."
    );
    process.exit(result.status || 1);
  }
  console.log(`Done. Point ${spec.prefix}_MODEL at a .gguf under ${path.relative(ROOT, dest)}/`);
}

const USAGE = `Usage: node deploy/scripts/llama-serve.mjs <${Object.keys(MODELS).join("|")}> serve|stop|restart|verify|warmup|download`;
const [modelName, cmd = "serve"] = process.argv.slice(2);
const spec = MODELS[modelName];
if (!spec) {
  console.error(USAGE);
  process.exit(2);
}
const cfg = resolve(spec);

if (cmd === "serve") await serve(spec, cfg);
else if (cmd === "stop") stop(spec, cfg);
else if (cmd === "restart") {
  stop(spec, cfg);
  waitForPortRelease(cfg.port, 5000);
  await serve(spec, cfg);
} else if (cmd === "verify") await verify(spec, cfg);
else if (cmd === "warmup") await spec.warmup({ port: cfg.port, alias: cfg.src.alias, force: true });
else if (cmd === "download") download(spec, cfg);
else {
  console.error(USAGE);
  process.exit(2);
}
