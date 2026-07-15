#!/usr/bin/env node
/**
 * Solo llama-server NuExtract bench (no Repody).
 * Accuracy gate: total_amount ≈ 6000.00 on Facture PNG.
 */
import { spawn, spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { killListenerPort, parseEnvFile } from "../scripts/runtime-env.mjs";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const LLAMA_DIR = path.join(ROOT, "deploy/llamacpp");
const PATHS = parseEnvFile(path.join(LLAMA_DIR, "paths.local.env"));
const PORT = Number(PATHS.LLAMACPP_PORT || 8081);
const EXE = PATHS.LLAMACPP_EXE;
const MODEL = PATHS.LLAMACPP_MODEL;
const MMPROJ = PATHS.LLAMACPP_MMPROJ;
const ALIAS = PATHS.LLAMACPP_MODEL_ALIAS || "nuextract3-q4_k_m";
// Prefer NuExtract-DPI render of Facture.pdf (same as Repody); fall back to PNG.
const IMAGE_PDF_RENDER = path.join(LLAMA_DIR, "logs/facture-page0.png");
const IMAGE_PNG = path.join(
  ROOT,
  "e2e/fixtures/documents/Facture RETOUCHE remplie AVEC TVA.png",
);
const IMAGE = fs.existsSync(IMAGE_PDF_RENDER) ? IMAGE_PDF_RENDER : IMAGE_PNG;
const LOG_DIR = path.join(LLAMA_DIR, "logs");

const SETUPS = [
  {
    name: "A-fa-on-min1024",
    args: ["-fa", "on", "--image-min-tokens", "1024"],
    env: {},
  },
  {
    name: "C-fa-on-ub1024",
    args: [
      "-fa",
      "on",
      "--image-min-tokens",
      "1024",
      "-ub",
      "1024",
      "--mtmd-batch-max-tokens",
      "1024",
    ],
    env: {},
  },
  {
    name: "D-fa-on-ub1024-imax1024",
    args: [
      "-fa",
      "on",
      "--image-min-tokens",
      "1024",
      "--image-max-tokens",
      "1024",
      "-ub",
      "1024",
      "--mtmd-batch-max-tokens",
      "1024",
    ],
    env: {},
  },
  {
    name: "F-fa-off-ub1024-imax1024",
    args: [
      "-fa",
      "off",
      "--image-min-tokens",
      "1024",
      "--image-max-tokens",
      "1024",
      "-ub",
      "1024",
      "--mtmd-batch-max-tokens",
      "1024",
    ],
    env: {},
  },
];

function baseArgs(extra) {
  return [
    "-m",
    MODEL,
    "--mmproj",
    MMPROJ,
    "--host",
    "127.0.0.1",
    "--port",
    String(PORT),
    "-c",
    "16384",
    "-np",
    "1",
    "-ngl",
    "99",
    "--device",
    "Vulkan0",
    "--mmproj-offload",
    "-a",
    ALIAS,
    "--jinja",
    "-rea",
    "off",
    ...extra,
  ];
}

async function waitReady(timeoutMs = 180_000) {
  const t0 = Date.now();
  while (Date.now() - t0 < timeoutMs) {
    try {
      const r = await fetch(`http://127.0.0.1:${PORT}/v1/models`);
      if (r.ok) return true;
    } catch {
      // retry
    }
    await new Promise((r) => setTimeout(r, 1500));
  }
  return false;
}

function stop() {
  killListenerPort(PORT);
  try {
    spawnSync("taskkill", ["/F", "/IM", "llama-server.exe"], {
      encoding: "utf8",
      stdio: "ignore",
    });
  } catch {
    // ignore
  }
}

function start(setup) {
  fs.mkdirSync(LOG_DIR, { recursive: true });
  const out = path.join(LOG_DIR, `bench-${setup.name}.out.log`);
  const err = path.join(LOG_DIR, `bench-${setup.name}.err.log`);
  const args = baseArgs(setup.args);
  console.log(`\n=== ${setup.name} ===`);
  console.log("args:", args.filter((_, i) => i === 0 || !["-m", "--mmproj"].includes(args[i - 1])).join(" "));
  const child = spawn(EXE, args, {
    cwd: LLAMA_DIR,
    detached: true,
    stdio: ["ignore", fs.openSync(out, "w"), fs.openSync(err, "w")],
    env: { ...process.env, ...setup.env },
  });
  child.unref();
  return { out, err };
}

function parseAmount(text) {
  try {
    const start = text.indexOf("{");
    const end = text.lastIndexOf("}");
    if (start < 0 || end <= start) return null;
    const obj = JSON.parse(text.slice(start, end + 1));
    const v = obj.total_amount ?? obj.fields?.find?.((f) => f.name === "total_amount")?.value;
    if (v == null) return null;
    const n = Number(String(v).replace(",", ".").replace(/[^\d.-]/g, ""));
    return Number.isFinite(n) ? n : null;
  } catch {
    return null;
  }
}

async function extractOnce() {
  const b64 = fs.readFileSync(IMAGE).toString("base64");
  const payload = {
    model: ALIAS,
    temperature: 0.2,
    messages: [
      {
        role: "user",
        content: [
          {
            type: "image_url",
            image_url: { url: `data:image/png;base64,${b64}` },
          },
        ],
      },
    ],
    // Official NuExtract leaf types (HF docs), not JSON-Schema objects.
    chat_template_kwargs: {
      template: JSON.stringify({ total_amount: "number" }),
      enable_thinking: false,
    },
  };
  const t0 = Date.now();
  const res = await fetch(`http://127.0.0.1:${PORT}/v1/chat/completions`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(payload),
  });
  const ms = Date.now() - t0;
  const body = await res.json().catch(() => ({}));
  const text = body?.choices?.[0]?.message?.content || body?.error?.message || JSON.stringify(body);
  const amount = parseAmount(text);
  const ok = res.ok && amount != null && Math.abs(amount - 6000) <= 0.05;
  return { ok, ms, amount, status: res.status, preview: String(text).slice(0, 200) };
}

async function runSetup(setup) {
  stop();
  await new Promise((r) => setTimeout(r, 4000));
  start(setup);
  const ready = await waitReady();
  if (!ready) {
    return { name: setup.name, error: "server not ready", coldMs: null, warmMs: null, ok: false };
  }
  let cold;
  let warm;
  try {
    cold = await extractOnce();
    warm = await extractOnce();
  } catch (e) {
    return { name: setup.name, error: String(e), coldMs: null, warmMs: null, ok: false };
  }
  return {
    name: setup.name,
    ok: cold.ok && warm.ok,
    coldMs: cold.ms,
    warmMs: warm.ms,
    coldAmount: cold.amount,
    warmAmount: warm.amount,
    coldPreview: cold.preview,
    warmPreview: warm.preview,
  };
}

async function main() {
  if (!fs.existsSync(IMAGE)) {
    console.error("Missing fixture:", IMAGE);
    process.exit(1);
  }
  if (!fs.existsSync(EXE) || !fs.existsSync(MODEL) || !fs.existsSync(MMPROJ)) {
    console.error("Missing LLAMACPP paths in paths.local.env");
    process.exit(1);
  }

  const ver = spawnSync(EXE, ["--version"], { encoding: "utf8" });
  console.log("llama-server:", (ver.stdout || ver.stderr || "").trim().split("\n")[0]);
  console.log("image:", path.basename(IMAGE));

  const results = [];
  for (const setup of SETUPS) {
    const r = await runSetup(setup);
    results.push(r);
    console.log(JSON.stringify(r, null, 2));
  }

  stop();
  console.log("\n=== SUMMARY ===");
  const good = results.filter((r) => r.ok);
  for (const r of results) {
    const mark = r.ok ? "PASS" : "FAIL";
    console.log(
      `${mark} ${r.name}: cold=${r.coldMs ?? "-"}ms warm=${r.warmMs ?? "-"}ms amount=${r.warmAmount ?? r.coldAmount ?? r.error}`,
    );
  }
  if (!good.length) {
    console.error("\nNo accurate setup passed.");
    process.exit(1);
  }
  good.sort((a, b) => (a.warmMs ?? 1e12) - (b.warmMs ?? 1e12));
  console.log("\nFastest accurate (warm):", good[0].name, `${good[0].warmMs}ms`);
  fs.writeFileSync(
    path.join(LOG_DIR, "bench-solo-results.json"),
    JSON.stringify({ at: new Date().toISOString(), results, winner: good[0] }, null, 2),
  );
}

await main();
