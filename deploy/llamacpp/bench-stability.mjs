#!/usr/bin/env node
/**
 * A/B: which Arc Vulkan stability flags are actually required.
 * Accuracy gate: total_amount ≈ 6000 on Facture.pdf @ 170 DPI.
 * Also stress-tests the large Facture PNG once per setup.
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
const LOG_DIR = path.join(LLAMA_DIR, "logs");
const PDF_IMG = path.join(LOG_DIR, "facture-page0.png");
const BIG_PNG = path.join(
  ROOT,
  "e2e/fixtures/documents/Facture RETOUCHE remplie AVEC TVA.png",
);

const SETUPS = [
  {
    name: "1-baseline-no-stability",
    args: ["-fa", "on", "--image-min-tokens", "1024"],
    env: {},
  },
  {
    name: "2-coopmat-only",
    args: ["-fa", "on", "--image-min-tokens", "1024"],
    env: { GGML_VK_DISABLE_COOPMAT: "1" },
  },
  {
    name: "3-coopmat1+2",
    args: ["-fa", "on", "--image-min-tokens", "1024"],
    env: { GGML_VK_DISABLE_COOPMAT: "1", GGML_VK_DISABLE_COOPMAT2: "1" },
  },
  {
    name: "4-coopmat-ub1024",
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
    env: { GGML_VK_DISABLE_COOPMAT: "1" },
  },
  {
    name: "5-full-current",
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
    env: { GGML_VK_DISABLE_COOPMAT: "1" },
  },
  {
    name: "6-full+coopmat2",
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
    env: { GGML_VK_DISABLE_COOPMAT: "1", GGML_VK_DISABLE_COOPMAT2: "1" },
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

function stopHard() {
  killListenerPort(PORT);
  spawnSync("taskkill", ["/F", "/IM", "llama-server.exe"], {
    encoding: "utf8",
    stdio: "ignore",
  });
}

async function waitReady(timeoutMs = 120_000) {
  const t0 = Date.now();
  while (Date.now() - t0 < timeoutMs) {
    try {
      const r = await fetch(`http://127.0.0.1:${PORT}/v1/models`);
      if (r.ok) return true;
    } catch {
      // retry
    }
    await new Promise((r) => setTimeout(r, 1200));
  }
  return false;
}

function start(setup) {
  fs.mkdirSync(LOG_DIR, { recursive: true });
  const out = path.join(LOG_DIR, `stab-${setup.name}.out.log`);
  const err = path.join(LOG_DIR, `stab-${setup.name}.err.log`);
  const args = baseArgs(setup.args);
  console.log(`\n=== ${setup.name} ===`);
  console.log("env:", JSON.stringify(setup.env));
  console.log(
    "extra:",
    setup.args.join(" "),
  );
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
    const v = obj.total_amount;
    if (v == null) return null;
    const n = Number(String(v).replace(",", ".").replace(/[^\d.-]/g, ""));
    return Number.isFinite(n) ? n : null;
  } catch {
    return null;
  }
}

function lastErr(errPath) {
  if (!fs.existsSync(errPath)) return "";
  const lines = fs.readFileSync(errPath, "utf8").trim().split(/\r?\n/);
  return lines.slice(-6).join(" | ");
}

async function extract(imagePath) {
  const b64 = fs.readFileSync(imagePath).toString("base64");
  const mime = imagePath.toLowerCase().endsWith(".png") ? "image/png" : "image/jpeg";
  const t0 = Date.now();
  let res;
  try {
    res = await fetch(`http://127.0.0.1:${PORT}/v1/chat/completions`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        model: ALIAS,
        temperature: 0.2,
        messages: [
          {
            role: "user",
            content: [
              {
                type: "image_url",
                image_url: { url: `data:${mime};base64,${b64}` },
              },
            ],
          },
        ],
        chat_template_kwargs: {
          template: JSON.stringify({ total_amount: "number" }),
          enable_thinking: false,
        },
      }),
    });
  } catch (e) {
    return {
      ok: false,
      ms: Date.now() - t0,
      amount: null,
      error: String(e),
      preview: "",
    };
  }
  const ms = Date.now() - t0;
  const body = await res.json().catch(() => ({}));
  const text =
    body?.choices?.[0]?.message?.content ||
    body?.error?.message ||
    JSON.stringify(body);
  const amount = parseAmount(text);
  const ok = res.ok && amount != null && Math.abs(amount - 6000) <= 0.05;
  return {
    ok,
    ms,
    amount,
    error: res.ok ? null : `HTTP ${res.status}`,
    preview: String(text).slice(0, 160),
  };
}

async function runSetup(setup) {
  stopHard();
  await new Promise((r) => setTimeout(r, 4000));
  const { err } = start(setup);
  const ready = await waitReady();
  if (!ready) {
    return {
      name: setup.name,
      ready: false,
      pdf: null,
      big: null,
      errTail: lastErr(err),
    };
  }

  const pdfCold = await extract(PDF_IMG);
  const pdfWarm = await extract(PDF_IMG);
  let big = null;
  if (fs.existsSync(BIG_PNG)) {
    big = await extract(BIG_PNG);
  }

  return {
    name: setup.name,
    ready: true,
    pdfCold,
    pdfWarm,
    big,
    errTail: lastErr(err),
    deviceLost: /ErrorDeviceLost|failed to process image/i.test(
      fs.existsSync(err) ? fs.readFileSync(err, "utf8") : "",
    ),
  };
}

async function main() {
  if (!fs.existsSync(PDF_IMG)) {
    console.error("Missing", PDF_IMG, "— render Facture.pdf first");
    process.exit(1);
  }
  const ver = spawnSync(EXE, ["--version"], { encoding: "utf8" });
  console.log("llama-server:", (ver.stdout || ver.stderr || "").trim().split("\n")[0]);
  console.log("device: Vulkan0 Intel Arc 140V");

  const results = [];
  for (const setup of SETUPS) {
    const r = await runSetup(setup);
    results.push(r);
    console.log(
      JSON.stringify(
        {
          name: r.name,
          ready: r.ready,
          deviceLost: r.deviceLost,
          pdfCold: r.pdfCold && {
            ok: r.pdfCold.ok,
            ms: r.pdfCold.ms,
            amount: r.pdfCold.amount,
            error: r.pdfCold.error,
          },
          pdfWarm: r.pdfWarm && {
            ok: r.pdfWarm.ok,
            ms: r.pdfWarm.ms,
            amount: r.pdfWarm.amount,
          },
          big: r.big && {
            ok: r.big.ok,
            ms: r.big.ms,
            amount: r.big.amount,
            error: r.big.error,
            preview: r.big.preview,
          },
        },
        null,
        2,
      ),
    );
  }

  stopHard();
  console.log("\n=== STABILITY SUMMARY ===");
  for (const r of results) {
    const pdfOk = r.pdfCold?.ok && r.pdfWarm?.ok;
    const bigOk = r.big?.ok;
    console.log(
      [
        r.name.padEnd(22),
        pdfOk ? "PDF=PASS" : "PDF=FAIL",
        `cold=${r.pdfCold?.ms ?? "-"}`,
        `warm=${r.pdfWarm?.ms ?? "-"}`,
        bigOk === true ? "BIG=PASS" : bigOk === false ? "BIG=FAIL" : "BIG=?",
        r.deviceLost ? "DEVICE_LOST" : "stable",
      ].join("  "),
    );
  }

  fs.writeFileSync(
    path.join(LOG_DIR, "bench-stability-results.json"),
    JSON.stringify({ at: new Date().toISOString(), results }, null, 2),
  );
}

await main();
