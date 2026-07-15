#!/usr/bin/env node
/** Minimal isolations after full A/B. */
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

const SETUPS = [
  {
    name: "A-imax-only",
    args: [
      "-fa",
      "on",
      "--image-min-tokens",
      "1024",
      "--image-max-tokens",
      "1024",
    ],
    env: {},
  },
  {
    name: "B-imax+coopmat",
    args: [
      "-fa",
      "on",
      "--image-min-tokens",
      "1024",
      "--image-max-tokens",
      "1024",
    ],
    env: { GGML_VK_DISABLE_COOPMAT: "1" },
  },
  {
    name: "C-imax+ub-no-coopmat",
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
    name: "D-full",
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
];

function stopHard() {
  killListenerPort(PORT);
  spawnSync("taskkill", ["/F", "/IM", "llama-server.exe"], {
    stdio: "ignore",
  });
}

async function waitReady(timeoutMs = 90_000) {
  const t0 = Date.now();
  while (Date.now() - t0 < timeoutMs) {
    try {
      if ((await fetch(`http://127.0.0.1:${PORT}/v1/models`)).ok) return true;
    } catch {}
    await new Promise((r) => setTimeout(r, 1000));
  }
  return false;
}

function start(setup) {
  const err = path.join(LOG_DIR, `stabmin-${setup.name}.err.log`);
  const out = path.join(LOG_DIR, `stabmin-${setup.name}.out.log`);
  const args = [
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
    ...setup.args,
  ];
  console.log(`\n=== ${setup.name} ===`, setup.env, setup.args.join(" "));
  spawn(EXE, args, {
    cwd: LLAMA_DIR,
    detached: true,
    stdio: ["ignore", fs.openSync(out, "w"), fs.openSync(err, "w")],
    env: { ...process.env, ...setup.env },
  }).unref();
  return err;
}

async function extract() {
  const b64 = fs.readFileSync(PDF_IMG).toString("base64");
  const t0 = Date.now();
  try {
    const res = await fetch(`http://127.0.0.1:${PORT}/v1/chat/completions`, {
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
                image_url: { url: `data:image/png;base64,${b64}` },
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
    const body = await res.json().catch(() => ({}));
    const text = body?.choices?.[0]?.message?.content || body?.error?.message || "";
    let amount = null;
    try {
      amount = JSON.parse(text).total_amount;
    } catch {}
    return {
      ok: res.ok && Number(amount) === 6000,
      ms: Date.now() - t0,
      amount,
      status: res.status,
      text: String(text).slice(0, 120),
    };
  } catch (e) {
    return { ok: false, ms: Date.now() - t0, error: String(e) };
  }
}

const results = [];
for (const setup of SETUPS) {
  stopHard();
  await new Promise((r) => setTimeout(r, 3500));
  const err = start(setup);
  if (!(await waitReady())) {
    results.push({ name: setup.name, ready: false });
    continue;
  }
  const cold = await extract();
  const warm = await extract();
  const log = fs.existsSync(err) ? fs.readFileSync(err, "utf8") : "";
  const deviceLost = /ErrorDeviceLost|failed to process image/i.test(log);
  const row = { name: setup.name, cold, warm, deviceLost };
  results.push(row);
  console.log(JSON.stringify(row));
}
stopHard();
console.log("\n=== MIN SUMMARY ===");
for (const r of results) {
  console.log(
    r.name.padEnd(24),
    r.cold?.ok ? "PASS" : "FAIL",
    `cold=${r.cold?.ms ?? "-"}`,
    r.deviceLost ? "DEVICE_LOST" : "ok",
  );
}
fs.writeFileSync(
  path.join(LOG_DIR, "bench-stability-min-results.json"),
  JSON.stringify({ at: new Date().toISOString(), results }, null, 2),
);
