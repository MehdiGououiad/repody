#!/usr/bin/env node
/**
 * Poll OCR worker logs for Repody VLM warmup completion.
 */
import { spawnSync } from "node:child_process";
import { setTimeout as sleep } from "node:timers/promises";
import { dockerComposeInvocation, dockerComposeRootArgs } from "../deploy/scripts/compose-docker-args.mjs";

const stack = process.env.AUDIT_COMPOSE_STACK ?? "dev";
const warmup = process.env.AUDIT_COMPOSE_WARMUP === "1";
const TIMEOUT_MS = Number(process.env.WARMUP_WAIT_TIMEOUT_MS ?? 600_000);
const INTERVAL_MS = 3_000;
const DONE_MARKER = "ocr_worker_warmup_done";
const FAILURE_MARKERS = ["repody_vlm_warmup_failed"];

function workerLogs() {
  const { fileArgs, profileArgs } = dockerComposeInvocation(stack, {
    warmup: warmup || undefined,
  });
  const result = spawnSync(
    "docker",
    ["compose", ...dockerComposeRootArgs(), ...fileArgs, ...profileArgs, "logs", "--tail", "300", "worker"],
    { encoding: "utf8" }
  );
  return `${result.stdout ?? ""}${result.stderr ?? ""}`;
}

function warmupFailed(logs) {
  return FAILURE_MARKERS.some((marker) => logs.includes(marker));
}

function warmupSummary(logs) {
  const match = logs.match(/ocr_worker_warmup_done[^\n]*/);
  return match?.[0] ?? null;
}

async function main() {
  const deadline = Date.now() + TIMEOUT_MS;
  process.stderr.write("Waiting for OCR worker warmup (Repody VLM)…");

  while (Date.now() < deadline) {
    const logs = workerLogs();
    if (warmupFailed(logs)) {
      process.stderr.write("\n");
      console.error("OCR worker warmup failed. Check worker logs for repody_vlm_warmup_failed.");
      process.exit(1);
    }
    if (logs.includes(DONE_MARKER)) {
      process.stderr.write("\n");
      const summary = warmupSummary(logs);
      process.stderr.write(`✓ OCR worker warmup complete${summary ? ` — ${summary.trim()}` : ""}.\n`);
      return;
    }
    process.stderr.write(".");
    await sleep(INTERVAL_MS);
  }

  process.stderr.write("\n");
  console.error(
    `Warmup did not complete within ${Math.round(TIMEOUT_MS / 1000)}s. Check: pnpm compose logs --stack=${stack} worker`
  );
  process.exit(1);
}

main();
