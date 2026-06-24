#!/usr/bin/env node
/**
 * Run full platform E2E: live API journey (pytest) + browser tests (Playwright).
 * Prerequisites: local Kubernetes stack (pnpm k8s:local) and hosts file entries.
 */
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const apiURL = process.env.E2E_API_URL ?? "http://api.repody.local";
const webURL = process.env.E2E_WEB_URL ?? "http://app.repody.local";

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
    await new Promise((r) => setTimeout(r, 2000));
  }
  console.error(
    `[platform-e2e] Timed out waiting for ${label} at ${url}\n` +
      `  Start the stack: pnpm k8s:local:hosts && pnpm k8s:local\n` +
      `  Check status: pnpm k8s:local:status`,
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
