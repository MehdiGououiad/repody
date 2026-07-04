#!/usr/bin/env node
/**
 * Poll the API health endpoint until ready (or timeout).
 * Usage: node scripts/wait-for-api.mjs
 */
import { setTimeout as sleep } from "node:timers/promises";

const API_HOST = process.env.API_HEALTH_HOST ?? "api.repody.local";
const URL = process.env.API_HEALTH_URL ?? "http://127.0.0.1/v1/healthz/live";
const TIMEOUT_MS = Number(process.env.API_WAIT_TIMEOUT_MS ?? 300_000);
const INTERVAL_MS = 2_000;

async function ping() {
  const res = await fetch(URL, {
    signal: AbortSignal.timeout(8_000),
    headers: { Host: API_HOST },
  });
  return res.ok;
}

async function main() {
  const deadline = Date.now() + TIMEOUT_MS;
  process.stderr.write(`Waiting for API at ${URL}...`);

  while (Date.now() < deadline) {
    try {
      if (await ping()) {
        process.stderr.write("\nok: API is ready.\n");
        return;
      }
    } catch {
      // retry
    }
    await sleep(INTERVAL_MS);
    process.stderr.write(".");
  }

  process.stderr.write(
    `\nerror: Timed out waiting for API at ${URL}\n` +
      "  Ensure the cluster is up: pnpm dev\n" +
      "  Check pods: pnpm status\n",
  );
  process.exit(1);
}

main();

