#!/usr/bin/env node
/**
 * llama-server for NuExtract-2.0-2B GGUF (IE-tuned text/vision extraction).
 *
 * Official: https://huggingface.co/numind/NuExtract-2.0-2B-GGUF
 * Text IE prompt style: "# Template:\\n{json}\\n{text}"
 *
 * Usage: node deploy/scripts/research/nuextract2-serve.mjs serve|stop|restart|verify|warmup|download
 */
import { spawn, spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { killListenerPort, parseEnvFile, resolveExecutable } from "../runtime-env.mjs";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../..");
const DIR = path.join(ROOT, "deploy/research/nuextract2");
const PATHS_FILE = path.join(DIR, "paths.local.env");
const LOG_DIR = path.join(DIR, "logs");
const HF_REPO = "numind/NuExtract-2.0-2B-GGUF";
const DEFAULT_ALIAS = "NuExtract-2.0-2B";

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
  const model = env.NUEXTRACT2_MODEL?.trim();
  const mmproj = env.NUEXTRACT2_MMPROJ?.trim();
  let exe = env.NUEXTRACT2_EXE?.trim() || env.LLAMACPP_EXE?.trim() || findLlamaServerExe();
  const port = Number(env.NUEXTRACT2_PORT || 8085);
  const context = Number(env.NUEXTRACT2_CONTEXT || 8192);
  const gpuLayers = Number(env.NUEXTRACT2_GPU_LAYERS || 99);
  const device = env.NUEXTRACT2_DEVICE?.trim() || "";
  const parallel = Number(env.NUEXTRACT2_PARALLEL || 1);
  const modelAlias = (env.NUEXTRACT2_MODEL_ALIAS || DEFAULT_ALIAS).trim();
  const useHf =
    (env.NUEXTRACT2_USE_HF || "").trim().toLowerCase() === "true" ||
    (env.NUEXTRACT2_USE_HF || "").trim() === "1" ||
    !model;
  const missing = [];
  if (!exe || !fs.existsSync(exe)) missing.push("NUEXTRACT2_EXE (or llama-server on PATH)");
  if (!useHf) {
    if (!model || !fs.existsSync(model)) missing.push("NUEXTRACT2_MODEL");
    if (mmproj && !fs.existsSync(mmproj)) missing.push("NUEXTRACT2_MMPROJ");
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
    "--temp",
    "0.0",
    "--jinja",
  );
  if (paths.device) args.push("--device", paths.device);
  return args;
}

async function verify(port) {
  const url = `http://127.0.0.1:${port}/v1/models`;
  try {
    const { ok, status, body } = await fetchJson(url);
    if (!ok) {
      console.error(`NuExtract-2.0 not ready at ${url}: HTTP ${status}`);
      process.exit(1);
    }
    const ids = Array.isArray(body?.data) ? body.data.map((m) => m.id).filter(Boolean) : [];
    console.log(`NuExtract-2.0 OK — ${url}`);
    if (ids.length) console.log(`  models: ${ids.join(", ")}`);
  } catch (err) {
    console.error(`NuExtract-2.0 not reachable at ${url}: ${err}`);
    process.exit(1);
  }
}

async function warmup(port) {
  const paths = resolvePaths();
  const served = paths.modelAlias || DEFAULT_ALIAS;
  const url = `http://127.0.0.1:${port}/v1/chat/completions`;
  console.log(`Warming NuExtract-2.0 at ${url} (model=${served})…`);
  const started = Date.now();
  const res = await fetch(url, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      model: served,
      temperature: 0,
      max_tokens: 64,
      messages: [
        {
          role: "user",
          content: '# Template:\n{\n    "ok": "string"\n}\nText: ping',
        },
      ],
    }),
    signal: AbortSignal.timeout(180_000),
  });
  const text = await res.text();
  if (!res.ok) {
    console.error(`NuExtract-2.0 warmup HTTP ${res.status}: ${text.slice(0, 400)}`);
    process.exit(1);
  }
  console.log(`NuExtract-2.0 warmup OK — ${Date.now() - started}ms`);
}

async function serve() {
  const paths = resolvePaths();
  if (paths.missing.length) {
    console.error("Missing or invalid paths:", paths.missing.join(", "));
    console.error(`Copy ${path.join(DIR, "paths.local.env.example")} → paths.local.env`);
    process.exit(1);
  }
  try {
    const ping = await fetchJson(`http://127.0.0.1:${paths.port}/v1/models`);
    if (ping.ok) {
      console.log(`NuExtract-2.0 already listening on :${paths.port}`);
      await verify(paths.port);
      return;
    }
  } catch {
    // not running
  }

  fs.mkdirSync(LOG_DIR, { recursive: true });
  const outLog = path.join(LOG_DIR, "nuextract2.out.log");
  const errLog = path.join(LOG_DIR, "nuextract2.err.log");
  const args = buildArgs(paths);
  console.log(`Starting NuExtract-2.0 on :${paths.port}...`);
  if (paths.useHf) console.log(`  source: -hf ${HF_REPO}`);
  else {
    console.log(`  model:  ${paths.model}`);
    if (paths.mmproj) console.log(`  mmproj: ${paths.mmproj}`);
  }
  console.log(`  alias:  ${paths.modelAlias}`);
  console.log(`  logs:   ${LOG_DIR}`);

  const child = spawn(paths.exe, args, {
    cwd: DIR,
    detached: true,
    stdio: ["ignore", fs.openSync(outLog, "a"), fs.openSync(errLog, "a")],
    env: { ...process.env },
  });
  child.unref();

  const ready = await waitForServer(paths.port);
  if (!ready) {
    console.error("Timed out waiting for NuExtract-2.0. Check logs in", LOG_DIR);
    process.exit(1);
  }
  console.log("NuExtract-2.0 llama-server is up.");
  await verify(paths.port);
  if ((process.env.NUEXTRACT2_WARMUP || "on").trim().toLowerCase() !== "off") {
    await warmup(paths.port);
  }
  console.log(`  AUDIT_NUEXTRACT2_BASE_URL=http://127.0.0.1:${paths.port}/v1`);
}

function download() {
  const dest = path.join(DIR, "models");
  fs.mkdirSync(dest, { recursive: true });
  console.log(`Downloading ${HF_REPO} into ${dest} …`);
  const hf = resolveExecutable("hf");
  const result = spawnSync(hf, ["download", HF_REPO, "--local-dir", dest], {
    stdio: "inherit",
    shell: false,
  });
  if (result.status !== 0) {
    console.error("hf download failed.");
    process.exit(result.status || 1);
  }
  console.log("Done. Point NUEXTRACT2_MODEL / NUEXTRACT2_MMPROJ under deploy/research/nuextract2/models/");
}

const cmd = process.argv[2] || "serve";
if (cmd === "serve") void serve();
else if (cmd === "stop") {
  const port = Number(parseEnvFile(PATHS_FILE).NUEXTRACT2_PORT || process.env.NUEXTRACT2_PORT || 8085);
  killListenerPort(port);
  console.log(`Stopped NuExtract-2.0 on :${port} (if it was running).`);
} else if (cmd === "restart") {
  const port = Number(parseEnvFile(PATHS_FILE).NUEXTRACT2_PORT || process.env.NUEXTRACT2_PORT || 8085);
  killListenerPort(port);
  void serve();
} else if (cmd === "verify") {
  const port = Number(parseEnvFile(PATHS_FILE).NUEXTRACT2_PORT || process.env.NUEXTRACT2_PORT || 8085);
  void verify(port);
} else if (cmd === "warmup") {
  const port = Number(parseEnvFile(PATHS_FILE).NUEXTRACT2_PORT || process.env.NUEXTRACT2_PORT || 8085);
  void warmup(port);
} else if (cmd === "download") download();
else {
  console.error(
    "Usage: node deploy/scripts/nuextract2-serve.mjs serve|stop|restart|verify|warmup|download",
  );
  process.exit(2);
}
