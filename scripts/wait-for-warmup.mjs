#!/usr/bin/env node
/**
 * Poll OCR worker logs for Repody VLM warmup completion (Kubernetes).
 */
import { spawnSync } from "node:child_process";
import { setTimeout as sleep } from "node:timers/promises";

const ns = process.env.REPODY_K8S_NAMESPACE ?? "repody";
const TIMEOUT_MS = Number(process.env.WARMUP_WAIT_TIMEOUT_MS ?? 600_000);
const INTERVAL_MS = 3_000;
const DONE_MARKER = "ocr_worker_warmup_done";
const FAILURE_MARKERS = ["repody_vlm_warmup_failed"];

function workerLogs() {
  const result = spawnSync(
    "kubectl",
    [
      "-n",
      ns,
      "logs",
      "-l",
      "app.kubernetes.io/component=worker-ocr",
      "--tail=200",
      "--prefix=true",
    ],
    { encoding: "utf8" },
  );
  return (result.stdout ?? "") + (result.stderr ?? "");
}

async function main() {
  const deadline = Date.now() + TIMEOUT_MS;
  process.stderr.write("Waiting for OCR worker VLM warmup…");

  while (Date.now() < deadline) {
    const logs = workerLogs();
    if (logs.includes(DONE_MARKER)) {
      process.stderr.write("\n✓ OCR worker warmup complete.\n");
      return;
    }
    if (FAILURE_MARKERS.some((m) => logs.includes(m))) {
      process.stderr.write("\n✗ OCR worker warmup failed (see worker logs).\n");
      process.exit(1);
    }
    await sleep(INTERVAL_MS);
    process.stderr.write(".");
  }

  process.stderr.write(
    "\n✗ Timed out waiting for OCR worker warmup.\n" +
      "  Configure external inference with REPODY_VLLM_BASE_URL or check worker logs.\n",
  );
  process.exit(1);
}

main();
