#!/usr/bin/env node
/**
 * Official CPU / local GLM-OCR backend: Ollama (zai-org docs).
 *
 * Docs:
 *   https://github.com/zai-org/GLM-OCR/blob/main/examples/ollama-deploy/README.md
 *   https://huggingface.co/zai-org/GLM-OCR
 *
 *   ollama pull glm-ocr:latest
 *   ollama serve   # :11434
 *   SDK: api_mode=ollama_generate, api_path=/api/generate
 *
 * Default local backend (llama-server GGUF): pnpm glmocr:serve
 *
 * Usage: node deploy/scripts/glmocr-ollama-serve.mjs serve|stop|restart|verify|warmup|download
 */
import { spawn, spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { parseEnvFile, resolveExecutable } from "./runtime-env.mjs";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const GLM_DIR = path.join(ROOT, "deploy/glmocr");
const PATHS_FILE = path.join(GLM_DIR, "paths.local.env");
const LOG_DIR = path.join(GLM_DIR, "logs");
const PID_FILE = path.join(GLM_DIR, "ollama-serve.pid");
const DEFAULT_PORT = 11434;
const DEFAULT_MODEL = "glm-ocr:latest";

function resolveConfig() {
  const fileEnv = parseEnvFile(PATHS_FILE);
  const env = { ...fileEnv, ...process.env };
  return {
    port: Number(env.GLMOCR_PORT || env.OLLAMA_PORT || DEFAULT_PORT),
    // Prefer Ollama official model id; ignore leftover llama aliases like GLM-OCR.
    model: (() => {
      const raw = (
        env.GLMOCR_MODEL_ALIAS ||
        env.AUDIT_GLM_OCR_SERVED_MODEL ||
        DEFAULT_MODEL
      ).trim();
      if (!raw || raw.toUpperCase() === "GLM-OCR") return DEFAULT_MODEL;
      return raw;
    })(),
    host: (env.GLMOCR_HOST || "127.0.0.1").trim() || "127.0.0.1",
  };
}

function findOllama() {
  const fromEnv = (process.env.OLLAMA_EXE || "").trim();
  if (fromEnv && fs.existsSync(fromEnv)) return fromEnv;
  return resolveExecutable("ollama");
}

async function fetchJson(url, { method = "GET", body, timeoutMs = 30_000 } = {}) {
  const res = await fetch(url, {
    method,
    headers: body ? { "content-type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
    signal: AbortSignal.timeout(timeoutMs),
  });
  const text = await res.text();
  let parsed;
  try {
    parsed = JSON.parse(text);
  } catch {
    parsed = text;
  }
  return { ok: res.ok, status: res.status, body: parsed, text };
}

async function ollamaUp(host, port) {
  try {
    const { ok } = await fetchJson(`http://${host}:${port}/api/tags`);
    return ok;
  } catch {
    return false;
  }
}

async function waitForOllama(host, port, { timeoutMs = 120_000 } = {}) {
  const started = Date.now();
  while (Date.now() - started < timeoutMs) {
    if (await ollamaUp(host, port)) return true;
    await new Promise((r) => setTimeout(r, 1500));
  }
  return false;
}

function modelPresent(tagsBody, model) {
  const models = Array.isArray(tagsBody?.models) ? tagsBody.models : [];
  const want = model.toLowerCase();
  const wantBase = want.split(":")[0];
  return models.some((m) => {
    const name = String(m?.name || "").toLowerCase();
    return name === want || name === wantBase || name.startsWith(`${wantBase}:`);
  });
}

function pullModel(ollama, model) {
  console.log(`Pulling ${model} (official zai-org Ollama path)…`);
  const result = spawnSync(ollama, ["pull", model], { stdio: "inherit", shell: false });
  if (result.status !== 0) {
    console.error(`ollama pull ${model} failed`);
    process.exit(result.status || 1);
  }
}

async function ensureModel(host, port, ollama, model) {
  const { ok, body } = await fetchJson(`http://${host}:${port}/api/tags`);
  if (!ok) {
    console.error(`Cannot list Ollama models at http://${host}:${port}/api/tags`);
    process.exit(1);
  }
  if (modelPresent(body, model)) {
    console.log(`Model present: ${model}`);
    return;
  }
  pullModel(ollama, model);
}

async function verify() {
  const { host, port, model } = resolveConfig();
  const url = `http://${host}:${port}/api/tags`;
  try {
    const { ok, status, body } = await fetchJson(url);
    if (!ok) {
      console.error(`Ollama not ready at ${url}: HTTP ${status}`);
      process.exit(1);
    }
    if (!modelPresent(body, model)) {
      console.error(`Model ${model} not found. Run: pnpm glmocr:download`);
      process.exit(1);
    }
    console.log(`GLM-OCR OK — Ollama ${url}`);
    console.log(`  model: ${model}`);
    console.log(`  SDK:   api_mode=ollama_generate api_path=/api/generate`);
  } catch (err) {
    console.error(`Ollama not reachable at ${url}: ${err}`);
    process.exit(1);
  }
}

/** Official docs verification: POST /api/generate (no vision). */
async function warmup() {
  const { host, port, model } = resolveConfig();
  const url = `http://${host}:${port}/api/generate`;
  console.log(`Warming GLM-OCR at ${url} (model=${model})…`);
  const started = Date.now();
  let res;
  try {
    res = await fetchJson(url, {
      method: "POST",
      body: { model, prompt: "Text Recognition:", stream: false },
      timeoutMs: 180_000,
    });
  } catch (err) {
    console.error(`GLM-OCR warmup failed: ${err}`);
    process.exit(1);
  }
  if (!res.ok) {
    console.error(`GLM-OCR warmup HTTP ${res.status}: ${String(res.text).slice(0, 400)}`);
    process.exit(1);
  }
  console.log(`GLM-OCR warmup OK — ${Date.now() - started}ms`);
}

async function serve() {
  const { host, port, model } = resolveConfig();
  const ollama = findOllama();
  if (!ollama) {
    console.error("ollama not found on PATH.");
    console.error("Install from https://ollama.com/download (official GLM-OCR CPU path).");
    console.error(
      "Docs: https://github.com/zai-org/GLM-OCR/blob/main/examples/ollama-deploy/README.md"
    );
    process.exit(1);
  }

  if (await ollamaUp(host, port)) {
    console.log(`Ollama already listening on :${port}`);
  } else {
    fs.mkdirSync(LOG_DIR, { recursive: true });
    const outLog = path.join(LOG_DIR, "ollama.out.log");
    const errLog = path.join(LOG_DIR, "ollama.err.log");
    console.log(`Starting ollama serve on :${port}…`);
    console.log(
      `  docs: https://github.com/zai-org/GLM-OCR/blob/main/examples/ollama-deploy/README.md`
    );
    const child = spawn(ollama, ["serve"], {
      cwd: GLM_DIR,
      detached: true,
      stdio: ["ignore", fs.openSync(outLog, "a"), fs.openSync(errLog, "a")],
      env: {
        ...process.env,
        OLLAMA_HOST: `${host}:${port}`,
      },
    });
    if (child.pid) {
      fs.writeFileSync(PID_FILE, String(child.pid), "utf8");
    }
    child.unref();
    const ready = await waitForOllama(host, port);
    if (!ready) {
      console.error("Timed out waiting for Ollama. Check logs in", LOG_DIR);
      process.exit(1);
    }
    console.log("Ollama is up.");
  }

  await ensureModel(host, port, ollama, model);
  await verify();
  if ((process.env.GLMOCR_WARMUP || "off").trim().toLowerCase() === "on") {
    await warmup();
  }
  console.log(`  AUDIT_GLM_OCR_BASE_URL=http://${host}:${port}`);
  console.log(`  AUDIT_GLM_OCR_SERVED_MODEL=${model}`);
  console.log(`  Compose workers: http://host.docker.internal:${port}`);
}

function stopManaged() {
  const { host, port } = resolveConfig();
  if (!fs.existsSync(PID_FILE)) {
    console.log(`No managed Ollama pid (${PID_FILE}). Leaving system Ollama on :${port} running.`);
    console.log("To stop system Ollama, quit the Ollama app / service yourself.");
    return;
  }
  const raw = fs.readFileSync(PID_FILE, "utf8").trim();
  const pid = Number(raw);
  fs.unlinkSync(PID_FILE);
  if (!Number.isFinite(pid) || pid <= 0) {
    console.log("Invalid pid file; removed.");
    return;
  }
  try {
    process.kill(pid);
    console.log(`Stopped managed ollama serve (pid ${pid}) on :${port} (${host}).`);
  } catch (err) {
    console.log(`Managed pid ${pid} already gone (${err}).`);
  }
}

function download() {
  const ollama = findOllama();
  if (!ollama) {
    console.error("ollama not found on PATH. Install from https://ollama.com/download");
    process.exit(1);
  }
  const { model } = resolveConfig();
  pullModel(ollama, model);
}

const cmd = process.argv[2] || "serve";
if (cmd === "serve") void serve();
else if (cmd === "stop") stopManaged();
else if (cmd === "restart") {
  stopManaged();
  void serve();
} else if (cmd === "verify") void verify();
else if (cmd === "warmup") void warmup();
else if (cmd === "download") download();
else {
  console.error(
    "Usage: node deploy/scripts/glmocr-serve.mjs serve|stop|restart|verify|warmup|download"
  );
  process.exit(2);
}
