#!/usr/bin/env node
/**
 * Wait until the OCR worker reports Repody VLM warmup complete.
 * Usage: AUDIT_WARM_MODELS=repody-vlm node scripts/wait-for-warmup.mjs
 *
 * Compose stack must match the running containers (see AUDIT_COMPOSE_STACK).
 */
import { spawnSync } from "node:child_process";
import { composeFilesForStack } from "./compose-files.mjs";

const COMPOSE = composeFilesForStack(
  process.env.AUDIT_COMPOSE_STACK ?? "dev-warmup"
);
const TIMEOUT_MS = Number(process.env.WARMUP_WAIT_TIMEOUT_MS ?? 600_000);
const INTERVAL_MS = 5_000;
const MODELS = (process.env.AUDIT_WARM_MODELS ?? "repody-vlm")
  .split(",")
  .map((value) => value.trim().toLowerCase())
  .filter(Boolean);
const EVENTS = {
  "repody-vlm": "repody_vlm_warmup_done",
};

let composeLogsErrorShown = false;

function dockerLogs(service, tail = 400) {
  const result = spawnSync(
    "docker",
    ["compose", ...COMPOSE, "logs", service, `--tail=${tail}`],
    { encoding: "utf8" }
  );
  if (result.status !== 0 && !composeLogsErrorShown) {
    composeLogsErrorShown = true;
    const detail = (result.stderr ?? result.stdout ?? "").trim();
    console.error(
      "Could not read worker logs via docker compose.\n" +
        `  stack: ${COMPOSE.join(" ")}\n` +
        (detail ? `  ${detail}\n` : "") +
        "  Hint: AUDIT_COMPOSE_STACK must match how the stack was started " +
        "(dev-warmup for pnpm dev:warmup, prod-warmup for pnpm platform:start)."
    );
  }
  return result.stdout ?? "";
}

function warmupFailed(logs) {
  return /repody_vlm_warmup_failed/.test(logs);
}

async function main() {
  const deadline = Date.now() + TIMEOUT_MS;
  process.stderr.write(`Waiting for worker warmup: ${MODELS.join(", ")}...`);
  let ready = {};

  while (Date.now() < deadline) {
    const logs = dockerLogs("worker");
    ready = Object.fromEntries(
      MODELS.map((model) => [model, logs.includes(EVENTS[model] ?? "__unknown__")])
    );

    if (MODELS.every((model) => ready[model])) {
      process.stderr.write(`\nReady: ${MODELS.join(", ")}.\n`);
      return;
    }

    if (warmupFailed(logs) && Date.now() > deadline - TIMEOUT_MS + 60_000) {
      process.stderr.write("\n");
      console.error("Worker warmup failed. Check logs: pnpm platform:logs");
      process.exit(1);
    }

    const status = MODELS.map(
      (model) => `${model} ${ready[model] ? "ready" : "pending"}`
    ).join(" | ");
    process.stderr.write(`\n  ${status}`);
    await new Promise((resolve) => setTimeout(resolve, INTERVAL_MS));
  }

  process.stderr.write("\n");
  console.error(
    `Warmup did not complete within ${Math.round(TIMEOUT_MS / 1000)}s. ` +
      `Status: ${MODELS.map((model) => `${model}=${ready[model] ? "ok" : "pending"}`).join(", ")}. ` +
      "Check: docker compose logs worker (last lines should include repody_vlm_warmup_done)"
  );
  process.exit(1);
}

main();
