#!/usr/bin/env node
/**
 * Host llama-server for NuExtract3 (OpenAI-compatible, detached).
 *
 *   node deploy/scripts/llama-serve.mjs serve|stop|restart|verify|download [nuextract]
 *
 * NuExtract3, AUDIT_LLAMACPP_* — https://huggingface.co/numind/NuExtract3-GGUF
 *
 * Only what the model card and llama.cpp need: the weights, the served name, --jinja (the chat
 * template takes chat_template_kwargs) and a context per request. Everything else is llama.cpp's
 * default, including image resolution, batch sizes, flash attention and GPU offload.
 *
 * Settings come from deploy/llamacpp/paths.local.env, overridable by process env:
 *   LLAMACPP_* EXE, MODEL, MMPROJ (or HF repo:quant), MODEL_ALIAS, PORT, CONTEXT, PARALLEL, DEVICE,
 *   GPU_LAYERS
 */
import { spawn, spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import {
  fetchJson,
  fetchProbe,
  findExecutable,
  parseEnvFile,
  ROOT,
  resolveExecutable,
  waitForLlamaServer,
} from "./runtime-env.mjs";

const DIR = path.join(ROOT, "deploy/llamacpp");
const LOG_DIR = path.join(DIR, "logs");
const env = { ...parseEnvFile(path.join(DIR, "paths.local.env")), ...process.env };

const MODELS = {
  nuextract: {
    title: "NuExtract3",
    prefix: "LLAMACPP",
    hfRepo: "numind/NuExtract3-GGUF",
    port: "8081",
    alias: "nuextract3-q8_0",
    context: "32768",
    backendEnv: "AUDIT_LLAMACPP",
  },
};

const name = process.argv[3] || "nuextract";
const spec = MODELS[name];
if (!spec) {
  console.error(`Unknown model ${name}: use ${Object.keys(MODELS).join(" or ")}`);
  process.exit(2);
}
const get = (key, fallback = "") => env[`${spec.prefix}_${key}`]?.trim() || fallback;
const exe = get("EXE") || env.LLAMACPP_EXE?.trim() || findExecutable("llama-server");
const port = Number(get("PORT", spec.port));
const alias = get("MODEL_ALIAS", spec.alias);
const pidFile = path.join(LOG_DIR, `${name}-llama-server.pid`);

/** The weights: local files (MODEL + MMPROJ), or a Hugging Face repo:quant that llama.cpp fetches. */
function weightArgs() {
  if (get("MODEL")) return ["-m", get("MODEL"), "--mmproj", get("MMPROJ")];
  return ["-hf", get("HF")];
}

function buildArgs() {
  const args = [
    ...weightArgs(),
    ...["--host", "0.0.0.0", "--port", String(port), "-a", alias, "--jinja"],
    ...["-c", get("CONTEXT", spec.context), "-np", get("PARALLEL", "1")],
  ];
  if (get("GPU_LAYERS")) args.push("-ngl", get("GPU_LAYERS"));
  if (get("DEVICE")) args.push("--device", get("DEVICE"));
  return args;
}

function missingPaths() {
  const missing = [];
  if (!exe || !fs.existsSync(exe)) missing.push("LLAMACPP_EXE (or llama-server on PATH)");
  if (get("MODEL")) {
    if (!fs.existsSync(get("MODEL"))) missing.push(`${spec.prefix}_MODEL`);
    if (!get("MMPROJ") || !fs.existsSync(get("MMPROJ"))) missing.push(`${spec.prefix}_MMPROJ`);
  } else if (!get("HF")) {
    missing.push(`${spec.prefix}_MODEL and ${spec.prefix}_MMPROJ`);
  }
  return missing;
}

async function verify() {
  const url = `http://127.0.0.1:${port}/v1/models`;
  const res = await fetchJson(url).catch((err) => {
    console.error(`${spec.title} not reachable at ${url}: ${err}`);
    process.exit(1);
  });
  if (!res.ok) {
    console.error(`${spec.title} not ready at ${url}: HTTP ${res.status}`);
    process.exit(1);
  }
  const ids = (res.body?.data || []).map((m) => m.id).filter(Boolean);
  const multimodal = (res.body?.models?.[0]?.capabilities || []).includes("multimodal");
  console.log(`${spec.title} OK — ${url}`);
  console.log(`  models: ${ids.join(", ") || "(none)"}  multimodal: ${multimodal}`);
  const failures = [];
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
    console.log(`${spec.title} llama-server already listening on :${port}`);
    await verify();
    return;
  }

  fs.mkdirSync(LOG_DIR, { recursive: true });
  const args = buildArgs();
  console.log(`Starting ${spec.title} on :${port}...`);
  console.log(`  args: ${args.join(" ")}`);
  console.log(`  logs: ${LOG_DIR}`);
  const child = spawn(exe, args, {
    cwd: DIR,
    detached: true,
    stdio: [
      "ignore",
      fs.openSync(path.join(LOG_DIR, `${name}-llama-server.out.log`), "a"),
      fs.openSync(path.join(LOG_DIR, `${name}-llama-server.err.log`), "a"),
    ],
  });
  child.unref();
  fs.writeFileSync(pidFile, String(child.pid));

  // The first start may download the weights (-hf).
  if (!(await waitForLlamaServer(port, { timeoutMs: 1_800_000 }))) {
    console.error(`Timed out waiting for ${spec.title} llama-server. Check logs in`, LOG_DIR);
    process.exit(1);
  }
  console.log(`${spec.title} llama-server is up.`);
  await verify();
  console.log(`  ${spec.backendEnv}_BASE_URL=http://host.docker.internal:${port}/v1`);
  console.log(`  ${spec.backendEnv}_SERVED_MODEL=${alias}`);
}

/** Guards against a stale PID file whose PID the OS has since reused. */
function isLlamaServer(pid) {
  const r =
    process.platform === "win32"
      ? spawnSync("tasklist", ["/FI", `PID eq ${pid}`, "/FO", "CSV", "/NH"], { encoding: "utf8" })
      : spawnSync("ps", ["-p", String(pid), "-o", "comm="], { encoding: "utf8" });
  return /llama-server/i.test(r.stdout || "");
}

/** Stop the server we started (its PID file). Other programs on the port are left alone. */
function stop() {
  const pid = fs.existsSync(pidFile) ? Number(fs.readFileSync(pidFile, "utf8").trim()) : 0;
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
  fs.rmSync(pidFile, { force: true });
  console.log(`Stopped ${spec.title} on :${port} (if it was running).`);
}

/** NuExtract3 GGUFs into deploy/llamacpp/models. */
function download() {
  if (!spec.hfRepo) {
    console.log(
      `${spec.title} is downloaded by llama-server itself on first start (-hf ${spec.hf}).`
    );
    return;
  }
  const dest = path.join(DIR, "models");
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
  console.log(
    `Done. Point ${spec.prefix}_MODEL / ${spec.prefix}_MMPROJ at the .gguf files under ${dest}`
  );
}

const cmd = process.argv[2] || "serve";
if (cmd === "serve") await serve();
else if (cmd === "stop") stop();
else if (cmd === "restart") {
  stop();
  // Wait for the old server to answer no more before starting the new one.
  for (let i = 0; i < 25 && (await fetchProbe(`http://127.0.0.1:${port}/health`, 500)).ok; i++) {
    await sleep(200);
  }
  await serve();
} else if (cmd === "verify") await verify();
else if (cmd === "download") download();
else {
  console.error(
    "Usage: node deploy/scripts/llama-serve.mjs serve|stop|restart|verify|download [nuextract]"
  );
  process.exit(2);
}
