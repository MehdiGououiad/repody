#!/usr/bin/env node
/**
 * Run full platform E2E: the live API journey (pytest -m live: the demo workflow on a real
 * document, through Hatchet and the model) and the browser tests (Playwright).
 * Prerequisites: local platform (pnpm platform) or Kubernetes lab with hosts entries.
 */
import { spawnSync } from "node:child_process";
import path from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { fileURLToPath } from "node:url";
import { uvBackend } from "../deploy/scripts/runtime-env.mjs";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const apiURL = (process.env.E2E_API_URL ?? "http://127.0.0.1:8000").replace(/\/$/, "");
const webURL = process.env.E2E_WEB_URL ?? "http://localhost:3000";
const authURL = process.env.E2E_AUTH_URL ?? "http://127.0.0.1:8080";

async function waitForOk(url, label, attempts = 90) {
  for (let i = 0; i < attempts; i++) {
    try {
      const res = await fetch(url, { signal: AbortSignal.timeout(3000) });
      if (res.ok) {
        console.log(`[platform-e2e] ${label} ready: ${url}`);
        return;
      }
    } catch {
      /* retry */
    }
    await sleep(2000);
  }
  console.error(
    `[platform-e2e] Timed out waiting for ${label} at ${url}\n` +
      `  Start the stack: pnpm platform setup && pnpm platform\n` +
      `  Check status: pnpm platform status`
  );
  process.exit(1);
}

function run(cmd, args, cwd = root, extraEnv = {}, options = {}) {
  console.log(`\n[platform-e2e] ${cmd} ${args.join(" ")}\n`);
  const useShell = options.shell ?? false;
  const result = spawnSync(cmd, args, {
    cwd,
    stdio: "inherit",
    shell: useShell,
    env: { ...process.env, ...extraEnv },
  });
  if (result.error) {
    console.error(`[platform-e2e] Failed to start ${cmd}: ${result.error.message}`);
    process.exit(1);
  }
  if (result.status !== 0) process.exit(result.status ?? 1);
}

await waitForOk(`${apiURL}/v1/healthz`, "API");
await waitForOk(webURL, "Web");

const sharedEnv = { E2E_API_URL: apiURL, E2E_WEB_URL: webURL, E2E_AUTH_URL: authURL };

run(
  ...uvBackend(["python", "-m", "pytest", "tests/live", "-v", "-m", "live"], { dev: true }),
  root,
  sharedEnv
);

run("pnpm", ["exec", "playwright", "test"], root, sharedEnv, {
  shell: process.platform === "win32",
});

console.log("\n[platform-e2e] All platform tests passed.\n");
