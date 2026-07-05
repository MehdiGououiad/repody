#!/usr/bin/env node
/**
 * OCR load soak — enqueue concurrent runs and report success rate + duration percentiles.
 *
 *   pnpm ocr:soak -- --api-url http://localhost:8000 --workflow-id wf-invoice-audit --token $JWT
 *   pnpm ocr:soak -- --api-url $URL --concurrency 8 --duration-minutes 30 --poll-seconds 5
 *
 * Requires a deployed workflow with document bindings or uses test-run shape when --test-run is set.
 */
import { spawnSync } from "node:child_process";
import { setTimeout as sleep } from "node:timers/promises";

function parseArg(name, fallback = null) {
  const idx = process.argv.indexOf(name);
  return idx >= 0 && process.argv[idx + 1] ? process.argv[idx + 1] : fallback;
}

const apiUrl = (parseArg("--api-url", process.env.E2E_API_URL || "http://localhost:8000")).replace(
  /\/$/,
  "",
);
const workflowId = parseArg("--workflow-id", "wf-invoice-audit");
const token = parseArg("--token", process.env.OCR_SOAK_TOKEN || process.env.E2E_BEARER || "");
const concurrency = Math.max(1, parseInt(parseArg("--concurrency", "8"), 10) || 8);
const durationMinutes = Math.max(1, parseInt(parseArg("--duration-minutes", "30"), 10) || 30);
const pollSeconds = Math.max(2, parseInt(parseArg("--poll-seconds", "5"), 10) || 5);
const testRun = process.argv.includes("--test-run");

if (!token) {
  console.error("error: pass --token or set OCR_SOAK_TOKEN / E2E_BEARER");
  process.exit(1);
}

async function request(method, path, body) {
  const res = await fetch(`${apiUrl}${path}`, {
    method,
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: "application/json",
      ...(body ? { "Content-Type": "application/json" } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  const text = await res.text();
  let json = null;
  try {
    json = text ? JSON.parse(text) : null;
  } catch {
    json = null;
  }
  return { status: res.status, json, text };
}

async function createRun() {
  const path = `/v1/workflows/${workflowId}/runs/json`;
  const body = testRun
    ? {
        snapshot: {
          documents: [],
          rules: [],
          workflowName: "soak-test",
        },
      }
    : {};
  const { status, json } = await request("POST", path, body);
  if (status !== 200 && status !== 201 && status !== 202) {
    throw new Error(`create run failed: HTTP ${status} ${JSON.stringify(json)}`);
  }
  const runId = json?.runId || json?.run_id || json?.jobId;
  if (!runId) {
    throw new Error(`create run missing runId: ${JSON.stringify(json)}`);
  }
  return runId;
}

async function pollRun(runId, deadlineMs) {
  while (Date.now() < deadlineMs) {
    const { status, json } = await request("GET", `/v1/runs/${runId}`, null);
    if (status !== 200) {
      await sleep(pollSeconds * 1000);
      continue;
    }
    const runStatus = json?.status || json?.runStatus;
    if (runStatus === "done" || runStatus === "failed") {
      const started = json?.startedAt ? Date.parse(json.startedAt) : null;
      const finished = json?.finishedAt ? Date.parse(json.finishedAt) : Date.now();
      const durationMs = started ? finished - started : null;
      return { runId, status: runStatus, durationMs, overall: json?.overallStatus };
    }
    await sleep(pollSeconds * 1000);
  }
  return { runId, status: "timeout", durationMs: null, overall: null };
}

function percentile(sorted, p) {
  if (!sorted.length) {
    return null;
  }
  const idx = Math.min(sorted.length - 1, Math.ceil((p / 100) * sorted.length) - 1);
  return sorted[idx];
}

const endAt = Date.now() + durationMinutes * 60 * 1000;
const results = [];
let wave = 0;

console.error(
  `ocr-soak: api=${apiUrl} workflow=${workflowId} concurrency=${concurrency} duration=${durationMinutes}m`,
);

while (Date.now() < endAt) {
  wave += 1;
  const batch = [];
  for (let i = 0; i < concurrency; i += 1) {
    batch.push(
      (async () => {
        try {
          const runId = await createRun();
          return await pollRun(runId, endAt);
        } catch (err) {
          return {
            runId: null,
            status: "error",
            durationMs: null,
            overall: null,
            error: String(err),
          };
        }
      })(),
    );
  }
  const batchResults = await Promise.all(batch);
  results.push(...batchResults);
  const done = results.filter((r) => r.status === "done").length;
  const failed = results.filter((r) => r.status === "failed" || r.status === "error").length;
  console.error(
    `wave ${wave}: total=${results.length} done=${done} failed=${failed} timeout=${results.filter((r) => r.status === "timeout").length}`,
  );
  if (Date.now() >= endAt) {
    break;
  }
}

const terminal = results.filter((r) => r.status === "done" || r.status === "failed");
const successRate =
  terminal.length > 0 ? (results.filter((r) => r.status === "done").length / terminal.length) * 100 : 0;
const durations = results
  .map((r) => r.durationMs)
  .filter((d) => typeof d === "number" && d >= 0)
  .sort((a, b) => a - b);

const summary = {
  apiUrl,
  workflowId,
  concurrency,
  durationMinutes,
  totalRuns: results.length,
  done: results.filter((r) => r.status === "done").length,
  failed: results.filter((r) => r.status === "failed").length,
  errors: results.filter((r) => r.status === "error").length,
  timeouts: results.filter((r) => r.status === "timeout").length,
  successRatePercent: Math.round(successRate * 10) / 10,
  durationMs: {
    p50: percentile(durations, 50),
    p95: percentile(durations, 95),
    max: durations.length ? durations[durations.length - 1] : null,
  },
};

console.log(JSON.stringify(summary, null, 2));

const sloOk = summary.successRatePercent >= 99 && (summary.durationMs.p95 ?? 0) < 20 * 60 * 1000;
process.exit(sloOk ? 0 : 1);
