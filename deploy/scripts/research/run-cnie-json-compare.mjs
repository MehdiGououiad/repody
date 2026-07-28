#!/usr/bin/env node
/**
 * Sequential CNIE JSON compare:
 *   kill all → PP-OCRv6 (front+back) → kill → PP-StructureV3 → kill → Qwen JSON compare
 *
 * Never starts OCR / Structure / Qwen at the same time.
 *
 * Usage: node deploy/scripts/research/run-cnie-json-compare.mjs
 */
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../..");
const stamp = new Date().toISOString().replace(/[-:]/g, "").replace(/\.\d+Z$/, "Z");
const OUT_DIR = path.join(ROOT, "benchmark-reports", "cnie-structure-llm", stamp);

function run(label, cmd, args, { cwd = ROOT } = {}) {
  console.log(`\n======== ${label} ========`);
  console.log(`$ ${cmd} ${args.join(" ")}`);
  const result = spawnSync(cmd, args, {
    cwd,
    env: { ...process.env },
    stdio: "inherit",
    shell: false,
  });
  if (result.error) {
    throw new Error(`${label} spawn error: ${result.error.message}`);
  }
  if (result.signal) {
    throw new Error(`${label} killed by signal ${result.signal}`);
  }
  if (result.status !== 0) {
    throw new Error(`${label} failed with exit ${result.status}`);
  }
}

function nodeScript(rel, ...args) {
  run(`node ${rel} ${args.join(" ")}`, process.execPath, [path.join(ROOT, rel), ...args]);
}

function killAll() {
  console.log("\n======== kill all model servers ========");
  for (const rel of [
    "deploy/scripts/paddleocr-v6-serve.mjs",
    "deploy/scripts/research/paddleocr-structure-v3-serve.mjs",
    "deploy/scripts/research/qwen35-serve.mjs",
    "deploy/scripts/glmocr-serve.mjs",
    "deploy/scripts/llamacpp-nuextract3.mjs",
  ]) {
    spawnSync(process.execPath, [path.join(ROOT, rel), "stop"], {
      cwd: ROOT,
      stdio: "inherit",
      shell: false,
    });
  }
}

function bench(arm) {
  const args = [
    path.join(ROOT, "scripts/backend-run.mjs"),
    "--dev",
    "python",
    "scripts/research/cnie_structure_llm_bench.py",
    "--arm",
    arm,
    "--output-dir",
    OUT_DIR,
    "--from-dir",
    OUT_DIR,
    "--fail-on-error",
  ];
  if (arm === "structure") {
    args.push("--structure-mode", "http");
  }
  run(`bench --arm ${arm}`, process.execPath, args);
}

fs.mkdirSync(OUT_DIR, { recursive: true });
console.log(`Report dir: ${OUT_DIR}`);

try {
  killAll();

  // Phase 1: PP-OCRv6 only (two passes: front then back inside the arm)
  nodeScript("deploy/scripts/paddleocr-v6-serve.mjs", "serve");
  bench("ocr");
  nodeScript("deploy/scripts/paddleocr-v6-serve.mjs", "stop");

  // Phase 2: PP-StructureV3 only (official POST /layout-parsing)
  nodeScript("deploy/scripts/research/paddleocr-structure-v3-serve.mjs", "serve");
  bench("structure");
  nodeScript("deploy/scripts/research/paddleocr-structure-v3-serve.mjs", "stop");

  // Phase 3: Qwen only — JSON from OCR text vs Structure text
  const qwenEnv = path.join(ROOT, "deploy/research/qwen35/paths.local.env");
  const qwenExample = path.join(ROOT, "deploy/research/qwen35/paths.local.env.example");
  if (!fs.existsSync(qwenEnv)) {
    fs.copyFileSync(qwenExample, qwenEnv);
    console.log("Created deploy/research/qwen35/paths.local.env from example");
  }
  nodeScript("deploy/scripts/research/qwen35-serve.mjs", "serve");
  bench("json-compare");
  nodeScript("deploy/scripts/research/qwen35-serve.mjs", "stop");

  console.log(`\nDONE. Compare JSON at:\n  ${path.join(OUT_DIR, "report.md")}`);
  console.log(`  ${path.join(OUT_DIR, "ocr-llm.fields.json")}`);
  console.log(`  ${path.join(OUT_DIR, "structure-llm.fields.json")}`);
} catch (err) {
  console.error(err instanceof Error ? err.message : err);
  killAll();
  process.exit(1);
}
