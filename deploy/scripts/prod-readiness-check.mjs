#!/usr/bin/env node
/**
 * Production readiness gate — orchestrates deploy checks and optional staging HTTP probes.
 *
 *   pnpm prod:readiness
 *   pnpm prod:readiness -- --api-url https://api.staging.example.com
 */
import { spawnSync } from "node:child_process";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { commandFor } from "./runtime-env.mjs";

const root = resolve(fileURLToPath(new URL("../..", import.meta.url)));

function parseArg(name) {
  const idx = process.argv.indexOf(name);
  return idx >= 0 && process.argv[idx + 1] ? process.argv[idx + 1] : null;
}

const apiUrl = (parseArg("--api-url") || process.env.PROD_READINESS_API_URL || "").replace(/\/$/, "");

function run(label, cmd, args, { optional = false } = {}) {
  console.error(`\n> ${label}\n`);
  const result = spawnSync(commandFor(cmd), args, {
    stdio: "inherit",
    cwd: root,
    shell: false,
  });
  if (result.status !== 0) {
    if (optional) {
      console.error(`warn: ${label} skipped or failed (optional)\n`);
      return false;
    }
    console.error(`\nerror: ${label} failed\n`);
    process.exit(result.status ?? 1);
  }
  return true;
}

function fetchJson(url) {
  const curl = process.platform === "win32" ? "curl.exe" : "curl";
  const result = spawnSync(
    curl,
    ["-fsS", "--max-time", "12", "-H", "Accept: application/json", url],
    { encoding: "utf8", cwd: root },
  );
  if (result.status !== 0) {
    return null;
  }
  try {
    return JSON.parse(result.stdout);
  } catch {
    return null;
  }
}

function httpStatus(url) {
  const curl = process.platform === "win32" ? "curl.exe" : "curl";
  const outputSink = process.platform === "win32" ? "NUL" : "/dev/null";
  const result = spawnSync(
    curl,
    ["-sS", "-o", outputSink, "-w", "%{http_code}", "--max-time", "12", url],
    {
      encoding: "utf8",
      cwd: root,
      shell: false,
    },
  );
  if (result.status !== 0) {
    return null;
  }
  const code = parseInt(result.stdout.trim(), 10);
  return Number.isFinite(code) ? code : null;
}

run("Deploy check", "node", ["deploy/scripts/deploy-check.mjs"]);
run("Client integration check", "node", ["deploy/scripts/client-integration-check.mjs"]);

run(
  "Helm template (bundled + enterprise)",
  "helm",
  [
    "template",
    "repody",
    "deploy/helm/repody",
    "-f",
    "deploy/helm/repody/values.yaml",
    "-f",
    "deploy/helm/repody/values-common.yaml",
    "-f",
    "deploy/client/values-bundled.example.yaml",
    "-f",
    "deploy/client/values-enterprise.example.yaml",
  ],
);

if (!apiUrl) {
  console.error("\nprod-readiness: static checks passed.");
  console.error("Optional: re-run with --api-url https://api.staging.example.com for live probes.\n");
  process.exit(0);
}

console.error(`\n> Live probes against ${apiUrl}\n`);

const liveUrl = `${apiUrl}/v1/healthz/live`;
const readyUrl = `${apiUrl}/v1/healthz`;

const liveCode = httpStatus(liveUrl);
if (liveCode !== 200) {
  console.error(`FAIL: ${liveUrl} expected HTTP 200, got ${liveCode ?? "error"}`);
  process.exit(1);
}
console.error(`OK: liveness ${liveUrl} → 200`);

const readyCode = httpStatus(readyUrl);
const readyBody = fetchJson(readyUrl);
if (readyCode !== 200) {
  console.error(`FAIL: ${readyUrl} expected HTTP 200, got ${readyCode ?? "error"}`);
  if (readyBody) {
    console.error(JSON.stringify(readyBody, null, 2));
  }
  process.exit(1);
}
if (readyBody && readyBody.redisOk === false) {
  console.error("FAIL: readiness reports redisOk=false");
  process.exit(1);
}
console.error(`OK: readiness ${readyUrl} → 200 (redisOk=${readyBody?.redisOk ?? "unknown"})`);

console.error("\nprod-readiness: all checks passed.\n");
