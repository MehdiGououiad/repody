#!/usr/bin/env node
/**
 * Poll worker logs for Repody VLM warmup completion.
 */
import { spawnSync } from "node:child_process";
import { setTimeout as sleep } from "node:timers/promises";
import { dockerComposeInvocation, dockerComposeRootArgs } from "../deploy/scripts/compose-docker-args.mjs";

const stack = process.env.AUDIT_COMPOSE_STACK ?? "dev";
const warmup = process.env.AUDIT_COMPOSE_WARMUP === "1";
const TIMEOUT_MS = Number(process.env.WARMUP_WAIT_TIMEOUT_MS ?? 600_000);
const INTERVAL_MS = 3_000;
const MARKER = "repody_vlm_warmup_done";

function workerLogs() {
  const { fileArgs, profileArgs } = dockerComposeInvocation(stack, {
    warmup: warmup || undefined,
  });
  const result = spawnSync(
    "docker",
    ["compose", ...dockerComposeRootArgs(), ...fileArgs, ...profileArgs, "logs", "--tail", "200", "worker"],
    { encoding: "utf8" }
  );
  return `${result.stdout ?? ""}${result.stderr ?? ""}`;
}

async function main() {
  const deadline = Date.now() + TIMEOUT_MS;
  process.stderr.write("Waiting for Repody VLM warmup in worker logs…");

  while (Date.now() < deadline) {
    if (workerLogs().includes(MARKER)) {
      process.stderr.write("\n✓ Repody VLM warmup complete.\n");
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
