#!/usr/bin/env node
/**
 * Poll the API health endpoint until ready (or timeout).
 * Usage: node scripts/wait-for-api.mjs
 */
import { spawnSync } from "node:child_process";
import { dockerComposeInvocation, dockerComposeRootArgs } from "../deploy/scripts/compose-docker-args.mjs";

const URL = process.env.API_HEALTH_URL ?? "http://127.0.0.1:8000/v1/healthz/live";
const TIMEOUT_MS = Number(process.env.API_WAIT_TIMEOUT_MS ?? 180_000);
const INTERVAL_MS = 2_000;
const STACK = process.env.AUDIT_COMPOSE_STACK ?? "dev";
const WARMUP = process.env.AUDIT_COMPOSE_WARMUP === "1";

async function ping() {
  const res = await fetch(URL, { signal: AbortSignal.timeout(8_000) });
  return res.ok;
}

function apiContainerHint() {
  const warmupOverlay = WARMUP ? { warmup: true } : {};
  const { fileArgs, profileArgs } = dockerComposeInvocation(STACK, warmupOverlay);
  spawnSync(
    "docker",
    ["compose", ...dockerComposeRootArgs(), ...fileArgs, ...profileArgs, "logs", "--tail", "80", "api"],
    { stdio: "inherit" }
  );
}

async function main() {
  const deadline = Date.now() + TIMEOUT_MS;
  process.stderr.write(`Waiting for API at ${URL} (can take up to ~60s on first boot)…`);

  while (Date.now() < deadline) {
    try {
      if (await ping()) {
        process.stderr.write("\n✓ API is ready.\n");
        return;
      }
    } catch {
      // API still booting (migrations, Python imports, seed)
    }
    process.stderr.write(".");
    await new Promise((r) => setTimeout(r, INTERVAL_MS));
  }

  process.stderr.write("\n");
  console.error(
    `API did not respond within ${Math.round(TIMEOUT_MS / 1000)}s. Recent api logs:`
  );
  apiContainerHint();
  console.error(
    "\nIf you see postgres password errors, reset volumes: pnpm compose down --stack=dev --volumes"
  );
  process.exit(1);
}

main();
