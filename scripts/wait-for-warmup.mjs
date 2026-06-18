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
const MAX_LOG_BUFFER = 32 * 1024 * 1024;

function composeBaseArgs(fileArgs, profileArgs) {
  return ["compose", ...dockerComposeRootArgs(), ...fileArgs, ...profileArgs];
}

function workerContainerId(fileArgs, profileArgs) {
  const result = spawnSync(
    "docker",
    [...composeBaseArgs(fileArgs, profileArgs), "ps", "-q", "worker"],
    { encoding: "utf8" }
  );
  if (result.status !== 0) {
    return null;
  }
  return (result.stdout ?? "").trim().split(/\r?\n/).filter(Boolean)[0] ?? null;
}

function containerStartedAt(containerId) {
  const result = spawnSync(
    "docker",
    ["inspect", "-f", "{{.State.StartedAt}}", containerId],
    { encoding: "utf8" }
  );
  if (result.status !== 0) {
    return null;
  }
  const started = (result.stdout ?? "").trim();
  return started || null;
}

function workerLogs(fileArgs, profileArgs) {
  const containerId = workerContainerId(fileArgs, profileArgs);
  const args = [...composeBaseArgs(fileArgs, profileArgs), "logs", "--no-color"];
  if (containerId) {
    const since = containerStartedAt(containerId);
    if (since) {
      args.push("--since", since);
    }
  } else {
    args.push("--tail", "5000");
  }
  args.push("worker");

  const result = spawnSync("docker", args, {
    encoding: "utf8",
    maxBuffer: MAX_LOG_BUFFER,
  });
  return `${result.stdout ?? ""}${result.stderr ?? ""}`;
}

function warmupFailed(logs) {
  return FAILURE_MARKERS.some((marker) => logs.includes(marker));
}

function warmupSummary(logs) {
  const matches = [...logs.matchAll(/ocr_worker_warmup_done[^\n]*/g)];
  return matches.at(-1)?.[0] ?? null;
}

function warmupDone(logs) {
  return logs.includes(DONE_MARKER);
}

async function main() {
  const { fileArgs, profileArgs } = dockerComposeInvocation(stack, {
    warmup: warmup || undefined,
  });
  const deadline = Date.now() + TIMEOUT_MS;
  const startedAt = Date.now();
  let polls = 0;

  process.stderr.write(
    "Waiting for OCR worker warmup (Repody VLM) — first load can take several minutes…"
  );

  while (Date.now() < deadline) {
    const logs = workerLogs(fileArgs, profileArgs);
    if (warmupFailed(logs)) {
      process.stderr.write("\n");
      console.error("OCR worker warmup failed. Check worker logs for repody_vlm_warmup_failed.");
      spawnSync(
        "docker",
        [...composeBaseArgs(fileArgs, profileArgs), "logs", "--tail", "120", "worker"],
        { stdio: "inherit" }
      );
      process.exit(1);
    }
    if (warmupDone(logs)) {
      process.stderr.write("\n");
      const summary = warmupSummary(logs);
      process.stderr.write(`✓ OCR worker warmup complete${summary ? ` — ${summary.trim()}` : ""}.\n`);
      return;
    }

    polls += 1;
    process.stderr.write(".");
    if (polls % 10 === 0) {
      const elapsed = Math.round((Date.now() - startedAt) / 1000);
      process.stderr.write(` (${elapsed}s)`);
    }
    await sleep(INTERVAL_MS);
  }

  process.stderr.write("\n");
  console.error(
    `Warmup did not complete within ${Math.round(TIMEOUT_MS / 1000)}s. Recent worker logs:`
  );
  spawnSync(
    "docker",
    [...composeBaseArgs(fileArgs, profileArgs), "logs", "--tail", "120", "worker"],
    { stdio: "inherit" }
  );
  console.error(
    `\nTips: ensure Docker Model Runner is enabled; check model pull with pnpm models:pull; skip warmup with pnpm dev (no --warmup).`
  );
  process.exit(1);
}

main();
