#!/usr/bin/env node
/**
 * llama-server for GLM-OCR (ggml-org official GGUF pack).
 *
 * Official usage:
 *   llama-server -hf ggml-org/GLM-OCR-GGUF
 *   https://huggingface.co/ggml-org/GLM-OCR-GGUF
 *   https://huggingface.co/blog/ggml-org/using-ocr-models-with-llama-cpp
 *
 * Chat contract (zai-org/GLM-OCR): image first, then "Text Recognition:".
 * GGUF pack: ggml-org/GLM-OCR-GGUF (converted from zai-org/GLM-OCR).
 *
 * Usage: node deploy/scripts/glmocr-serve.mjs serve|stop|restart|verify|warmup|download
 */
import { spawn, spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { killListenerPort, parseEnvFile, resolveExecutable } from "./runtime-env.mjs";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const GLM_DIR = path.join(ROOT, "deploy/glmocr");
const PATHS_FILE = path.join(GLM_DIR, "paths.local.env");
const LOG_DIR = path.join(GLM_DIR, "logs");
const HF_REPO = "ggml-org/GLM-OCR-GGUF";
const DEFAULT_ALIAS = "GLM-OCR";

function findLlamaServerExe() {
  const probe = spawnSync("where.exe", ["llama-server"], { encoding: "utf8" });
  if (probe.status === 0) {
    const line = probe.stdout.split(/\r?\n/).find((l) => l.trim().endsWith("llama-server.exe"));
    if (line?.trim()) return line.trim();
  }
  const which = spawnSync("which", ["llama-server"], { encoding: "utf8" });
  if (which.status === 0 && which.stdout.trim()) return which.stdout.trim().split(/\r?\n/)[0];
  return null;
}

function resolvePaths() {
  const fileEnv = parseEnvFile(PATHS_FILE);
  const env = { ...fileEnv, ...process.env };
  const model = env.GLMOCR_MODEL?.trim();
  const mmproj = env.GLMOCR_MMPROJ?.trim();
  let exe = env.GLMOCR_EXE?.trim() || env.LLAMACPP_EXE?.trim() || findLlamaServerExe();
  const port = Number(env.GLMOCR_PORT || 8083);
  const context = Number(env.GLMOCR_CONTEXT || 8192);
  const gpuLayers = Number(env.GLMOCR_GPU_LAYERS || 99);
  const device = env.GLMOCR_DEVICE?.trim() || "";
  const parallel = Number(env.GLMOCR_PARALLEL || 1);
  const modelAlias = (env.GLMOCR_MODEL_ALIAS || DEFAULT_ALIAS).trim();
  const useHf =
    (env.GLMOCR_USE_HF || "").trim().toLowerCase() === "true" ||
    (env.GLMOCR_USE_HF || "").trim() === "1" ||
    !model;
  const missing = [];
  if (!exe || !fs.existsSync(exe)) missing.push("GLMOCR_EXE (or llama-server on PATH)");
  if (!useHf) {
    if (!model || !fs.existsSync(model)) missing.push("GLMOCR_MODEL");
    if (mmproj && !fs.existsSync(mmproj)) missing.push("GLMOCR_MMPROJ");
  }
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
    useHf,
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

async function waitForServer(port, { timeoutMs = 600_000 } = {}) {
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
  const args = [];
  if (paths.useHf) {
    args.push("-hf", HF_REPO);
  } else {
    args.push("-m", paths.model);
    if (paths.mmproj) args.push("--mmproj", paths.mmproj);
  }
  args.push(
    "--host",
    "0.0.0.0",
    "--port",
    String(paths.port),
    "-c",
    String(paths.context),
    "-np",
    String(paths.parallel),
    "-ngl",
    String(paths.gpuLayers),
    "-a",
    paths.modelAlias,
    // Official zai-org SDK page_loader: temperature 0.0, top_k 1 (greedy OCR).
    "--temp",
    "0.0",
    "--top-k",
    "1",
    "--top-p",
    "0.00001",
    "--repeat-penalty",
    "1.1",
    "--jinja",
  );
  if (paths.device) {
    args.push("--device", paths.device);
  }
  return args;
}

function stopServer(port) {
  killListenerPort(port);
}

async function verify(port) {
  const url = `http://127.0.0.1:${port}/v1/models`;
  try {
    const { ok, status, body } = await fetchJson(url);
    if (!ok) {
      console.error(`GLM-OCR not ready at ${url}: HTTP ${status}`);
      process.exit(1);
    }
    const ids = Array.isArray(body?.data) ? body.data.map((m) => m.id).filter(Boolean) : [];
    console.log(`GLM-OCR OK — ${url}`);
    if (ids.length) console.log(`  models: ${ids.join(", ")}`);
  } catch (err) {
    console.error(`GLM-OCR not reachable at ${url}: ${err}`);
    process.exit(1);
  }
}

/** 1×1 PNG — primes vision path without a real document. */
const WARMUP_PNG_B64 =
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==";

async function warmup(port) {
  const paths = resolvePaths();
  const served = paths.modelAlias || DEFAULT_ALIAS;
  const url = `http://127.0.0.1:${port}/v1/chat/completions`;
  console.log(`Warming GLM-OCR at ${url} (model=${served})…`);
  const started = Date.now();
  let res;
  try {
    res = await fetch(url, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        model: served,
        temperature: 0,
        max_tokens: 16,
        messages: [
          {
            role: "user",
            content: [
              {
                type: "image_url",
                image_url: { url: `data:image/png;base64,${WARMUP_PNG_B64}` },
              },
              { type: "text", text: "Text Recognition:" },
            ],
          },
        ],
      }),
      signal: AbortSignal.timeout(180_000),
    });
  } catch (err) {
    console.error(`GLM-OCR warmup failed: ${err}`);
    process.exit(1);
  }
  const text = await res.text();
  if (!res.ok) {
    console.error(`GLM-OCR warmup HTTP ${res.status}: ${text.slice(0, 400)}`);
    process.exit(1);
  }
  console.log(`GLM-OCR warmup OK — ${Date.now() - started}ms`);
}

async function serve() {
  const paths = resolvePaths();
  if (paths.missing.length) {
    console.error("Missing or invalid paths:", paths.missing.join(", "));
    console.error(`Copy ${path.join(GLM_DIR, "paths.local.env.example")} → paths.local.env`);
    console.error("Or install llama-server and use HF mode (default when local GGUF unset).");
    process.exit(1);
  }

  try {
    const ping = await fetchJson(`http://127.0.0.1:${paths.port}/v1/models`);
    if (ping.ok) {
      console.log(`GLM-OCR llama-server already listening on :${paths.port}`);
      await verify(paths.port);
      return;
    }
  } catch {
    // not running
  }

  fs.mkdirSync(LOG_DIR, { recursive: true });
  const outLog = path.join(LOG_DIR, "glmocr.out.log");
  const errLog = path.join(LOG_DIR, "glmocr.err.log");
  const args = buildArgs(paths);

  console.log(`Starting GLM-OCR on :${paths.port}...`);
  if (paths.useHf) {
    console.log(`  source: -hf ${HF_REPO}`);
  } else {
    console.log(`  model:  ${paths.model}`);
    if (paths.mmproj) console.log(`  mmproj: ${paths.mmproj}`);
  }
  console.log(`  alias:  ${paths.modelAlias}`);
  console.log(`  logs:   ${LOG_DIR}`);

  const child = spawn(paths.exe, args, {
    cwd: GLM_DIR,
    detached: true,
    stdio: ["ignore", fs.openSync(outLog, "a"), fs.openSync(errLog, "a")],
    env: { ...process.env },
  });
  child.unref();

  const ready = await waitForServer(paths.port);
  if (!ready) {
    console.error("Timed out waiting for GLM-OCR llama-server. Check logs in", LOG_DIR);
    process.exit(1);
  }
  console.log("GLM-OCR llama-server is up.");
  await verify(paths.port);
  if ((process.env.GLMOCR_WARMUP || "on").trim().toLowerCase() !== "off") {
    await warmup(paths.port);
  }
  console.log(`  AUDIT_GLM_OCR_BASE_URL=http://127.0.0.1:${paths.port}/v1`);
  console.log(`  Compose workers: http://host.docker.internal:${paths.port}/v1`);
}

function download() {
  const dest = path.join(GLM_DIR, "models");
  fs.mkdirSync(dest, { recursive: true });
  console.log(`Downloading ${HF_REPO} into ${dest} …`);
  const hf = resolveExecutable("hf");
  const result = spawnSync(hf, ["download", HF_REPO, "--local-dir", dest], {
    stdio: "inherit",
    shell: false,
  });
  if (result.status !== 0) {
    console.error(
      "hf download failed. Install Hugging Face CLI (`pip install huggingface_hub`) or use HF serve mode.",
    );
    process.exit(result.status || 1);
  }
  console.log("Done. Point GLMOCR_MODEL (and optional GLMOCR_MMPROJ) under deploy/glmocr/models/");
}

const cmd = process.argv[2] || "serve";
if (cmd === "serve") void serve();
else if (cmd === "stop") {
  const port = Number(parseEnvFile(PATHS_FILE).GLMOCR_PORT || process.env.GLMOCR_PORT || 8083);
  stopServer(port);
  console.log(`Stopped GLM-OCR on :${port} (if it was running).`);
} else if (cmd === "restart") {
  const port = Number(parseEnvFile(PATHS_FILE).GLMOCR_PORT || process.env.GLMOCR_PORT || 8083);
  stopServer(port);
  void serve();
} else if (cmd === "verify") {
  const port = Number(parseEnvFile(PATHS_FILE).GLMOCR_PORT || process.env.GLMOCR_PORT || 8083);
  void verify(port);
} else if (cmd === "warmup") {
  const port = Number(parseEnvFile(PATHS_FILE).GLMOCR_PORT || process.env.GLMOCR_PORT || 8083);
  void warmup(port);
} else if (cmd === "download") download();
else {
  console.error(
    "Usage: node deploy/scripts/glmocr-serve.mjs serve|stop|restart|verify|warmup|download",
  );
  process.exit(2);
}
