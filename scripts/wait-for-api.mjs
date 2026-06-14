#!/usr/bin/env node
/**
 * Poll the API health endpoint until ready (or timeout).
 * Usage: node scripts/wait-for-api.mjs
 */
const URL = process.env.API_HEALTH_URL ?? "http://127.0.0.1:8000/v1/healthz/live";
const TIMEOUT_MS = Number(process.env.API_WAIT_TIMEOUT_MS ?? 180_000);
const INTERVAL_MS = 2_000;

async function ping() {
  const res = await fetch(URL, { signal: AbortSignal.timeout(8_000) });
  return res.ok;
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
    `API did not respond within ${Math.round(TIMEOUT_MS / 1000)}s. Check: pnpm docker:logs:platform`
  );
  process.exit(1);
}

main();
