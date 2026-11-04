#!/usr/bin/env node
/**
 * Host llama-server for NuExtract3 (OpenAI-compatible, detached).
 *
 *   node deploy/scripts/llama-serve.mjs serve|stop|restart|verify|download
 *
 * Reads deploy/llamacpp/paths.local.env (LLAMACPP_*), overridable by process env.
 * Flags follow https://huggingface.co/numind/NuExtract3-GGUF and llama.cpp docs/multimodal.md.
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

const DIR = path.join(ROOT, "deploy/llamacpp");
const LOG_DIR = path.join(DIR, "logs");
const PID_FILE = path.join(LOG_DIR, "llama-server.pid");
const HF_REPO = "numind/NuExtract3-GGUF";
const CONTEXT = 16384;

const env = { ...parseEnvFile(path.join(DIR, "paths.local.env")), ...process.env };
const get = (key, fallback = "") => env[`LLAMACPP_${key}`]?.trim() || fallback;
const exe = get("EXE") || findExecutable("llama-server");
const model = get("MODEL");
const mmproj = get("MMPROJ");
const port = Number(get("PORT", "8081"));
const alias = get("MODEL_ALIAS") || aliasFromFile(model);

function aliasFromFile(modelPath) {
  // Local default is Q8_0 (deep-bench winner); HF "small local" pack is Q4_K_M.
  const base = modelPath ? path.basename(modelPath, ".gguf") : "";
  for (const [pattern, name] of [
    [/Q6_K/i, "nuextract3-q6_k"],
    [/Q5_K_M/i, "nuextract3-q5_k_m"],
    [/Q4_K_M/i, "nuextract3-q4_k_m"],
  ]) {
    if (pattern.test(base)) return name;
  }
  return "nuextract3-q8_0";
}

/** Newer LM Studio / llama.cpp builds dropped --mtmd-batch-max-tokens; `0` force-disables. */
function mtmdBatchArgs() {
  const raw = get("MTMD_BATCH_MAX_TOKENS");
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

function buildArgs() {
  const args = ["-m", model, "--mmproj", mmproj];
  args.push(
    ...["--host", "0.0.0.0", "--port", String(port)],
    ...["-c", get("CONTEXT", String(CONTEXT)), "-np", get("PARALLEL", "1")],
    ...["-ngl", get("GPU_LAYERS", "99"), "-a", alias],
    ...["-ub", get("UBATCH_SIZE", "1024"), "-fa", get("FLASH_ATTN", "on").toLowerCase()],
    // Qwen-VL accuracy floor: --image-min-tokens 1024 (do not lower). -rea off: no thinking.
    ...["--image-min-tokens", get("IMAGE_MIN_TOKENS", "1024")],
    ...["--image-max-tokens", get("IMAGE_MAX_TOKENS", "1024")],
    ...mtmdBatchArgs(),
    ...["--mmproj-offload", "--jinja", "-rea", "off"]
  );
  if (get("DEVICE")) args.push("--device", get("DEVICE"));
  return args;
}

function missingPaths() {
  const missing = [];
  if (!exe || !fs.existsSync(exe)) missing.push("LLAMACPP_EXE (or llama-server on PATH)");
  if (!model || !fs.existsSync(model)) missing.push("LLAMACPP_MODEL");
  if (!mmproj || !fs.existsSync(mmproj)) missing.push("LLAMACPP_MMPROJ");
  return missing;
}

async function verify() {
  const url = `http://127.0.0.1:${port}/v1/models`;
  const res = await fetchJson(url).catch((err) => {
    console.error(`NuExtract3 not reachable at ${url}: ${err}`);
    process.exit(1);
  });
  if (!res.ok) {
    console.error(`NuExtract3 not ready at ${url}: HTTP ${res.status}`);
    process.exit(1);
  }
  const ids = (res.body?.data || []).map((m) => m.id).filter(Boolean);
  const nCtx = res.body?.data?.[0]?.meta?.n_ctx;
  const multimodal = (res.body?.models?.[0]?.capabilities || []).includes("multimodal");
  const parallel = Number(get("PARALLEL", "1"));
  const minCtx = parallel > 1 ? Math.floor(CONTEXT / parallel) : CONTEXT;
  console.log(`NuExtract3 OK — ${url}`);
  console.log(`  models: ${ids.join(", ") || "(none)"}`);
  console.log(`  n_ctx: ${nCtx}  multimodal: ${multimodal}`);
  const failures = [];
  if (!(nCtx >= minCtx)) failures.push(`n_ctx ${nCtx} < ${minCtx} (parallel=${parallel})`);
  if (!multimodal) failures.push("multimodal capability missing (mmproj not loaded?)");
  if (!ids.includes(alias)) failures.push(`served model != expected ${alias}`);
  if (failures.length) {
    console.error("\nNOT READY:");
    for (const f of failures) console.error(`  - ${f}`);
    process.exit(1);
  }
}

async function serve() {
  const missing = missingPaths();
  if (missing.length) {
    console.error("Missing or invalid paths:", missing.join(", "));
    console.error(`Copy ${path.join(DIR, "paths.local.env.example")} → paths.local.env`);
    process.exit(1);
  }
  if ((await fetchJson(`http://127.0.0.1:${port}/v1/models`).catch(() => ({}))).ok) {
    console.log(`NuExtract3 llama-server already listening on :${port}`);
    await verify();
    return;
  }

  fs.mkdirSync(LOG_DIR, { recursive: true });
  const args = buildArgs();
  console.log(`Starting NuExtract3 on :${port}...`);
  console.log(`  args: ${args.join(" ")}`);
  console.log(`  logs: ${LOG_DIR}`);
  const serverEnv = { ...process.env };
  // Strip leftover CoopMat overrides so a stale user/system env cannot re-enable them.
  for (const key of ["GGML_VK_DISABLE_COOPMAT", "GGML_VK_DISABLE_COOPMAT2", "LLAMACPP_STABILITY"]) {
    delete serverEnv[key];
  }
  const child = spawn(exe, args, {
    cwd: DIR,
    detached: true,
    stdio: [
      "ignore",
      fs.openSync(path.join(LOG_DIR, "llama-server.out.log"), "a"),
      fs.openSync(path.join(LOG_DIR, "llama-server.err.log"), "a"),
    ],
    env: serverEnv,
  });
  child.unref();
  fs.writeFileSync(PID_FILE, String(child.pid));

  if (!(await waitForLlamaServer(port, { timeoutMs: 300_000 }))) {
    console.error("Timed out waiting for NuExtract3 llama-server. Check logs in", LOG_DIR);
    process.exit(1);
  }
  console.log("NuExtract3 llama-server is up.");
  await verify();
  console.log(`  AUDIT_LLAMACPP_BASE_URL=http://host.docker.internal:${port}/v1`);
  console.log(`  AUDIT_LLAMACPP_SERVED_MODEL=${alias}`);
}

/** Guards against a stale PID file whose PID the OS has since reused. */
function isLlamaServer(pid) {
  const r =
    process.platform === "win32"
      ? spawnSync("tasklist", ["/FI", `PID eq ${pid}`, "/FO", "CSV", "/NH"], { encoding: "utf8" })
      : spawnSync("ps", ["-p", String(pid), "-o", "comm="], { encoding: "utf8" });
  return /llama-server/i.test(r.stdout || "");
}

/** Kill the server we started (PID file), then anything still bound to the port. */
function stop() {
  const pid = fs.existsSync(PID_FILE) ? Number(fs.readFileSync(PID_FILE, "utf8").trim()) : 0;
  if (pid > 0 && isLlamaServer(pid)) {
    if (process.platform === "win32") {
      spawnSync("taskkill", ["/PID", String(pid), "/T", "/F"], { stdio: "ignore" });
    } else {
      try {
        process.kill(pid, "SIGTERM");
      } catch {
        // already gone
      }
    }
  }
  fs.rmSync(PID_FILE, { force: true });
  killListenerPort(port);
  console.log(`Stopped NuExtract3 on :${port} (if it was running).`);
}

function download() {
  const dest = path.join(DIR, "models");
  fs.mkdirSync(dest, { recursive: true });
  console.log(`Downloading ${HF_REPO} into ${dest} …`);
  const result = spawnSync(resolveExecutable("hf"), ["download", HF_REPO, "--local-dir", dest], {
    stdio: "inherit",
    shell: false,
  });
  if (result.status !== 0) {
    console.error(
      "hf download failed. Install the Hugging Face CLI (`pip install huggingface_hub`)."
    );
    process.exit(result.status || 1);
  }
  console.log(`Done. Point LLAMACPP_MODEL / LLAMACPP_MMPROJ at the .gguf files under ${dest}`);
}

const cmd = process.argv[2] || "serve";
if (cmd === "serve") await serve();
else if (cmd === "stop") stop();
else if (cmd === "restart") {
  stop();
  waitForPortRelease(port, 5000);
  await serve();
} else if (cmd === "verify") await verify();
else if (cmd === "download") download();
else {
  console.error("Usage: node deploy/scripts/llama-serve.mjs serve|stop|restart|verify|download");
  process.exit(2);
}
