import type { RunAuditDetail } from "@/lib/types/audit";
import { humanizeRunError } from "@/lib/api/api-error";
import { browserApi, throwOnApiError } from "@/lib/api/openapi-client";
import { watchRunEvents } from "@/lib/api/run-events";

export type RunProgressStep = {
  id: string;
  label: string;
  status: "pending" | "active" | "done";
  mode?: "ocr" | "schema" | "text" | "auto" | "vlm" | "document_model";
  kind?: "logic" | "llm";
  detail?: string;
  readPath?: string;
  validationMode?: string;
  ocrModel?: string;
  durationMs?: number;
  cacheHit?: boolean;
  gpuColdStartHint?: boolean;
};

export type RunProgress = {
  currentIndex: number;
  steps: RunProgressStep[];
  label: string;
  queuePosition?: number;
  queueDepth?: number;
};

type RunPollResponse = {
  status: string;
  progress?: RunProgress;
  result?: RunAuditDetail;
  error?: string;
};

const DEFAULT_RUN_TIMEOUT_MS = 13 * 60_000;
const MIN_POLL_INTERVAL_MS = 400;
const MAX_POLL_INTERVAL_MS = 8_000;
const RATE_LIMIT_POLL_INTERVAL_MS = 4_000;

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function retryAfterMs(response: Response): number | null {
  const raw = response.headers.get("retry-after");
  if (!raw) return null;
  const seconds = Number(raw);
  if (Number.isFinite(seconds)) return Math.max(0, seconds * 1000);
  const dateMs = Date.parse(raw);
  if (Number.isFinite(dateMs)) return Math.max(0, dateMs - Date.now());
  return null;
}

function withJitter(ms: number): number {
  return Math.round(ms * (0.85 + Math.random() * 0.3));
}

function nextPollInterval(currentMs: number, body: RunPollResponse): number {
  const queued = body.status === "queued" || body.progress?.queuePosition != null;
  const floor = queued ? RATE_LIMIT_POLL_INTERVAL_MS : MIN_POLL_INTERVAL_MS;
  return Math.min(MAX_POLL_INTERVAL_MS, Math.max(floor, currentMs + 200));
}

export async function fetchRunDetail(runId: string): Promise<RunAuditDetail> {
  const { data, error, response } = await browserApi.GET("/v1/runs/{run_id}", {
    params: { path: { run_id: runId } },
  });
  if (error || !response.ok || !data) throwOnApiError(error, response);
  const body = data as RunPollResponse;
  if (!body.result) throw new Error("Run finished without result payload");
  return body.result;
}

/** Poll `/runs/{id}/status` until done, then fetch full audit detail. */
export async function pollRunUntilDone(
  runId: string,
  onProgress?: (progress: RunProgress) => void,
  maxMs = DEFAULT_RUN_TIMEOUT_MS
): Promise<RunAuditDetail> {
  const started = Date.now();
  let intervalMs = 400;
  while (Date.now() - started < maxMs) {
    const { data, error, response } = await browserApi.GET("/v1/runs/{run_id}/status", {
      params: { path: { run_id: runId } },
    });
    if (response.status === 429) {
      const retryMs = retryAfterMs(response) ?? Math.max(RATE_LIMIT_POLL_INTERVAL_MS, intervalMs * 2);
      intervalMs = Math.min(MAX_POLL_INTERVAL_MS, retryMs);
      await sleep(withJitter(intervalMs));
      continue;
    }
    if (error || !response.ok || !data) throwOnApiError(error, response);
    const body = data as RunPollResponse;
    if (body.progress) onProgress?.(body.progress);
    if (body.status === "done") return fetchRunDetail(runId);
    if (body.status === "failed") {
      throw new Error(
        humanizeRunError(body.error || "Run failed", {
          step: "Audit worker",
          runId,
        })
      );
    }
    intervalMs = nextPollInterval(intervalMs, body);
    await sleep(withJitter(intervalMs));
  }
  throw new Error(
    humanizeRunError("Run timed out - check worker and Docker Model Runner logs", {
      step: "Audit worker",
      runId,
    })
  );
}

/** SSE-first wait with polling fallback. */
export async function waitForRunUntilDone(
  runId: string,
  onProgress?: (progress: RunProgress) => void,
  options?: { maxMs?: number; headers?: HeadersInit }
): Promise<RunAuditDetail> {
  const maxMs = options?.maxMs ?? DEFAULT_RUN_TIMEOUT_MS;
  const outcome = await watchRunEvents(runId, onProgress, { maxMs, headers: options?.headers });

  if (outcome === "failed") {
    const { data, error, response } = await browserApi.GET("/v1/runs/{run_id}/status", {
      params: { path: { run_id: runId } },
    });
    if (error || !response.ok || !data) throwOnApiError(error, response);
    const body = data as RunPollResponse;
    throw new Error(
      humanizeRunError(body.error || "Run failed", {
        step: "Audit worker",
        runId,
      })
    );
  }

  if (outcome === "done") {
    return fetchRunDetail(runId);
  }

  return pollRunUntilDone(runId, onProgress, maxMs);
}
