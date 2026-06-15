#!/usr/bin/env node
/**
 * Run full platform E2E: live API journey (pytest) + browser tests (Playwright).
 * Prerequisites: API on :8000, web on :3000 (e.g. pnpm compose up --stack=dev --detach + pnpm dev).
 */
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const apiURL = process.env.E2E_API_URL ?? "http://localhost:8000";
const webURL = process.env.E2E_WEB_URL ?? "http://localhost:3000";

async function waitForOk(url, label, attempts = 60) {
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
    await new Promise((r) => setTimeout(r, 2000));
  }
  console.error(
    `[platform-e2e] Timed out waiting for ${label} at ${url}\n` +
      `  Start the stack: pnpm compose up --stack=dev --detach && pnpm dev\n` +
      `  Or: pnpm compose up --stack=prod --build --detach`
  );
  process.exit(1);
}

function run(cmd, args, cwd = root, extraEnv = {}) {
  console.log(`\n[platform-e2e] ${cmd} ${args.join(" ")}\n`);
  const result = spawnSync(cmd, args, {
    cwd,
    stdio: "inherit",
    shell: process.platform === "win32",
    env: { ...process.env, ...extraEnv },
  });
  if (result.status !== 0) process.exit(result.status ?? 1);
}

await waitForOk(`${apiURL}/v1/healthz`, "API");
await waitForOk(webURL, "Web");

run("python", ["scripts/platform_integration_suite.py"], path.join(root, "backend"), {
  E2E_API_URL: apiURL,
});

run("python", ["-m", "pytest", "tests/test_platform", "-v", "-m", "live"], path.join(root, "backend"), {
  E2E_API_URL: apiURL,
});

run("pnpm", ["exec", "playwright", "test"], root, {
  E2E_API_URL: apiURL,
  E2E_WEB_URL: webURL,
});

console.log("\n[platform-e2e] All platform tests passed.\n");
