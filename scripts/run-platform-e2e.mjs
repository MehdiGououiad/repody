#!/usr/bin/env node
/**
 * Run full platform E2E: live API journey (pytest) + browser tests (Playwright).
 * Prerequisites: local dev stack (pnpm dev) or Kubernetes lab with hosts entries.
 */
import { spawnSync } from "node:child_process";
import { setTimeout as sleep } from "node:timers/promises";
import { fileURLToPath } from "node:url";
import path from "node:path";

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
      `  Start the stack: pnpm dev:setup && pnpm dev:all\n` +
      `  Check status: pnpm dev:status`,
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

async function fetchKeycloakToken() {
  const body = new URLSearchParams({
    grant_type: "password",
    client_id: process.env.E2E_KEYCLOAK_CLIENT_ID ?? "repody-web",
    client_secret: process.env.E2E_KEYCLOAK_CLIENT_SECRET ?? "repody-web-dev-secret",
    username: process.env.E2E_KEYCLOAK_USER ?? "operator@repody.local",
    password: process.env.E2E_KEYCLOAK_PASSWORD ?? "repody-dev",
  });
  const res = await fetch(`${authURL}/realms/repody/protocol/openid-connect/token`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
    signal: AbortSignal.timeout(15_000),
  });
  if (!res.ok) {
    throw new Error(`Keycloak token request failed: ${res.status}`);
  }
  const json = await res.json();
  if (!json.access_token) {
    throw new Error("Keycloak response missing access_token");
  }
  return json.access_token;
}

async function resolveAccessToken() {
  try {
    const health = await fetch(`${apiURL}/v1/healthz`, { signal: AbortSignal.timeout(5000) });
    if (!health.ok) return process.env.REPODY_ACCESS_TOKEN?.trim() ?? "";
    const body = await health.json();
    if (!body.oidcEnabled) return process.env.REPODY_ACCESS_TOKEN?.trim() ?? "";
    const token = await fetchKeycloakToken();
    console.log("[platform-e2e] Acquired Keycloak bearer token for integration suite");
    return token;
  } catch (error) {
    console.warn("[platform-e2e] Could not fetch Keycloak token:", error.message ?? error);
    return process.env.REPODY_ACCESS_TOKEN?.trim() ?? "";
  }
}

await waitForOk(`${apiURL}/v1/healthz`, "API");
await waitForOk(webURL, "Web");

const accessToken = await resolveAccessToken();
const sharedEnv = {
  E2E_API_URL: apiURL,
  E2E_WEB_URL: webURL,
  E2E_AUTH_URL: authURL,
  ...(accessToken ? { REPODY_ACCESS_TOKEN: accessToken } : {}),
};

run(
  process.execPath,
  ["scripts/backend-run.mjs", "--dev", "python", "scripts/platform_integration_suite.py", "--api", apiURL],
  root,
  sharedEnv,
);

run(
  process.execPath,
  [
    "scripts/backend-run.mjs",
    "--dev",
    "python",
    "-m",
    "pytest",
    "tests/test_platform",
    "-v",
    "-m",
    "live",
  ],
  root,
  sharedEnv,
);

run(
  process.platform === "win32" ? "pnpm" : "pnpm",
  ["exec", "playwright", "test"],
  root,
  sharedEnv,
  { shell: process.platform === "win32" },
);

console.log("\n[platform-e2e] All platform tests passed.\n");
