#!/usr/bin/env node
/**
 * llama-server for Unsloth Qwen3.5-4B GGUF (text→JSON experiment arm).
 *
 * Official pack:
 *   https://huggingface.co/unsloth/Qwen3.5-4B-GGUF
 *
 * Usage: node deploy/scripts/research/qwen35-serve.mjs serve|stop|restart|verify|warmup|download
 */
import { spawn, spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { killListenerPort, parseEnvFile, resolveExecutable } from "../runtime-env.mjs";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../..");
const QWEN_DIR = path.join(ROOT, "deploy/research/qwen35");
const PATHS_FILE = path.join(QWEN_DIR, "paths.local.env");
const LOG_DIR = path.join(QWEN_DIR, "logs");
const HF_REPO = "unsloth/Qwen3.5-4B-GGUF";
const DEFAULT_ALIAS = "Qwen3.5-4B";

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
  const model = env.QWEN35_MODEL?.trim();
  const hfFile = env.QWEN35_HF_FILE?.trim() || "";
  let exe = env.QWEN35_EXE?.trim() || env.LLAMACPP_EXE?.trim() || findLlamaServerExe();
  const port = Number(env.QWEN35_PORT || 8084);
  const context = Number(env.QWEN35_CONTEXT || 8192);
  const gpuLayers = Number(env.QWEN35_GPU_LAYERS || 99);
  const device = env.QWEN35_DEVICE?.trim() || "";
  const parallel = Number(env.QWEN35_PARALLEL || 1);
  const modelAlias = (env.QWEN35_MODEL_ALIAS || DEFAULT_ALIAS).trim();
  const useHf =
    (env.QWEN35_USE_HF || "").trim().toLowerCase() === "true" ||
    (env.QWEN35_USE_HF || "").trim() === "1" ||
    !model;
  const missing = [];
  if (!exe || !fs.existsSync(exe)) missing.push("QWEN35_EXE (or llama-server on PATH)");
  if (!useHf && (!model || !fs.existsSync(model))) missing.push("QWEN35_MODEL");
  return {
    model,
    hfFile,
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
    if (paths.hfFile) args.push("--hf-file", paths.hfFile);
  } else {
    args.push("-m", paths.model);
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
    "--temp",
    "0.0",
    "--jinja",
    // Qwen3.5 defaults to thinking; disable for JSON extraction.
    "--reasoning",
    "off",
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
      console.error(`Qwen3.5-4B not ready at ${url}: HTTP ${status}`);
      process.exit(1);
    }
    const ids = Array.isArray(body?.data) ? body.data.map((m) => m.id).filter(Boolean) : [];
    console.log(`Qwen3.5-4B OK — ${url}`);
    if (ids.length) console.log(`  models: ${ids.join(", ")}`);
  } catch (err) {
    console.error(`Qwen3.5-4B not reachable at ${url}: ${err}`);
    process.exit(1);
  }
}

async function warmup(port) {
  const paths = resolvePaths();
  const served = paths.modelAlias || DEFAULT_ALIAS;
  const url = `http://127.0.0.1:${port}/v1/chat/completions`;
  console.log(`Warming Qwen3.5-4B at ${url} (model=${served})…`);
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
          { role: "system", content: "Reply with a single JSON object only." },
          { role: "user", content: 'Return {"ok":true}' },
        ],
      }),
      signal: AbortSignal.timeout(180_000),
    });
  } catch (err) {
    console.error(`Qwen3.5-4B warmup failed: ${err}`);
    process.exit(1);
  }
  const text = await res.text();
  if (!res.ok) {
    console.error(`Qwen3.5-4B warmup HTTP ${res.status}: ${text.slice(0, 400)}`);
    process.exit(1);
  }
  console.log(`Qwen3.5-4B warmup OK — ${Date.now() - started}ms`);
}

async function serve() {
  const paths = resolvePaths();
  if (paths.missing.length) {
    console.error("Missing or invalid paths:", paths.missing.join(", "));
    console.error(`Copy ${path.join(QWEN_DIR, "paths.local.env.example")} → paths.local.env`);
    console.error("Or install llama-server and use HF mode (default when local GGUF unset).");
    process.exit(1);
  }

  try {
    const ping = await fetchJson(`http://127.0.0.1:${paths.port}/v1/models`);
    if (ping.ok) {
      console.log(`Qwen3.5-4B llama-server already listening on :${paths.port}`);
      await verify(paths.port);
      return;
    }
  } catch {
    // not running
  }

  fs.mkdirSync(LOG_DIR, { recursive: true });
  const outLog = path.join(LOG_DIR, "qwen35.out.log");
  const errLog = path.join(LOG_DIR, "qwen35.err.log");
  const args = buildArgs(paths);

  console.log(`Starting Qwen3.5-4B on :${paths.port}...`);
  if (paths.useHf) {
    console.log(`  source: -hf ${HF_REPO}${paths.hfFile ? ` --hf-file ${paths.hfFile}` : ""}`);
  } else {
    console.log(`  model:  ${paths.model}`);
  }
  console.log(`  alias:  ${paths.modelAlias}`);
  console.log(`  logs:   ${LOG_DIR}`);

  const child = spawn(paths.exe, args, {
    cwd: QWEN_DIR,
    detached: true,
    stdio: ["ignore", fs.openSync(outLog, "a"), fs.openSync(errLog, "a")],
    env: { ...process.env },
  });
  child.unref();

  const ready = await waitForServer(paths.port);
  if (!ready) {
    console.error("Timed out waiting for Qwen3.5-4B llama-server. Check logs in", LOG_DIR);
    process.exit(1);
  }
  console.log("Qwen3.5-4B llama-server is up.");
  await verify(paths.port);
  if ((process.env.QWEN35_WARMUP || "on").trim().toLowerCase() !== "off") {
    await warmup(paths.port);
  }
  console.log(`  AUDIT_QWEN35_BASE_URL=http://127.0.0.1:${paths.port}/v1`);
}

function download() {
  const dest = path.join(QWEN_DIR, "models");
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
  console.log("Done. Point QWEN35_MODEL under deploy/research/qwen35/models/");
}

const cmd = process.argv[2] || "serve";
if (cmd === "serve") void serve();
else if (cmd === "stop") {
  const port = Number(parseEnvFile(PATHS_FILE).QWEN35_PORT || process.env.QWEN35_PORT || 8084);
  stopServer(port);
  console.log(`Stopped Qwen3.5-4B on :${port} (if it was running).`);
} else if (cmd === "restart") {
  const port = Number(parseEnvFile(PATHS_FILE).QWEN35_PORT || process.env.QWEN35_PORT || 8084);
  stopServer(port);
  void serve();
} else if (cmd === "verify") {
  const port = Number(parseEnvFile(PATHS_FILE).QWEN35_PORT || process.env.QWEN35_PORT || 8084);
  void verify(port);
} else if (cmd === "warmup") {
  const port = Number(parseEnvFile(PATHS_FILE).QWEN35_PORT || process.env.QWEN35_PORT || 8084);
  void warmup(port);
} else if (cmd === "download") download();
else {
  console.error(
    "Usage: node deploy/scripts/qwen35-serve.mjs serve|stop|restart|verify|warmup|download",
  );
  process.exit(2);
}
