import type { RunAuditDetail } from "@/lib/types/audit";
import { humanizeRunError } from "@/lib/api/api-error";
import { browserJson } from "@/lib/api/http";
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

export async function fetchRunDetail(runId: string): Promise<RunAuditDetail> {
  const body = await browserJson<RunPollResponse>(`/runs/${runId}`);
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
    const body = await browserJson<RunPollResponse>(`/runs/${runId}/status`);
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
    await new Promise((r) => setTimeout(r, intervalMs));
    intervalMs = Math.min(2000, intervalMs + 200);
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
    const body = await browserJson<RunPollResponse>(`/runs/${runId}/status`);
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
