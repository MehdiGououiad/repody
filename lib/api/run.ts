/**
 * One workflow run from the browser: post the files (multipart) to start the run, then
 * follow it to the end. Progress comes from SSE, with a poll that keeps the queue position
 * fresh and finishes the run if the stream drops.
 */
import { fetchEventSource } from "@microsoft/fetch-event-source";
import { formatApiError, raiseRunError } from "@/lib/api/api-error";
import { workflowAuthHeaders } from "@/lib/api/auth-policy";
import { browserApi } from "@/lib/api/openapi-client";
import type { RunProgress } from "@/lib/api/schema-types";
import { isFullWorkflowApiKey } from "@/lib/api/workflow-api-key";
import type { DocumentDef, WorkflowRule } from "@/lib/types";
import type { RunAuditDetail } from "@/lib/types/audit";

export type { RunProgress };
export type RunProgressStep = RunProgress["steps"][number];

const CLIENT_STEPS = ["save-workflow", "start-run", "poll-run"] as const;

export type ClientStepId = (typeof CLIENT_STEPS)[number];
export type ClientStepLabels = Record<ClientStepId, { label: string; pendingDetail?: string }>;

/** Client-side steps with `activeId` live: earlier steps done, later ones pending. */
export function clientProgress(labels: ClientStepLabels, activeId: ClientStepId): RunProgress {
  const activeIndex = CLIENT_STEPS.indexOf(activeId);
  const steps = CLIENT_STEPS.map((id, index): RunProgressStep => {
    const status = index < activeIndex ? "done" : index === activeIndex ? "active" : "pending";
    return {
      id,
      label: labels[id].label,
      status,
      detail: status === "done" ? null : (labels[id].pendingDetail ?? null),
      durationMs: null,
      cacheHit: false,
    };
  });
  return { label: labels[activeId].label, steps, queuePosition: null, queueDepth: null };
}

/** Client steps (all done) followed by the worker's own step plan. */
function withWorkerSteps(client: RunProgress, worker: RunProgress): RunProgress {
  return {
    ...worker,
    label: worker.label || client.label,
    steps: [
      ...client.steps.map((step) => ({ ...step, status: "done" as const, detail: null })),
      ...worker.steps.map((step) => ({ ...step, id: `worker-${step.id}` })),
    ],
  };
}

export type RunReporter = {
  clientLabels?: ClientStepLabels;
  onProgress?: (progress: RunProgress) => void;
};

function report(reporter: RunReporter | undefined, stepId: ClientStepId) {
  if (reporter?.clientLabels && reporter.onProgress) {
    reporter.onProgress(clientProgress(reporter.clientLabels, stepId));
  }
}

// --- Follow a run ---

const DEFAULT_RUN_TIMEOUT_MS = 10 * 60_000;
type Terminal = "done" | "failed";

function sleep(ms: number, signal: AbortSignal): Promise<void> {
  return new Promise((resolve) => {
    const timer = setTimeout(resolve, ms * (0.85 + Math.random() * 0.3));
    signal.addEventListener("abort", () => {
      clearTimeout(timer);
      resolve();
    });
  });
}

/** Resolves on the run's terminal SSE event; never resolves if the stream drops. */
function streamUntilTerminal(
  runId: string,
  onProgress: (progress: RunProgress) => void,
  signal: AbortSignal
): Promise<Terminal> {
  return new Promise((resolve) => {
    fetchEventSource(`/api/v1/runs/${runId}/events`, {
      signal,
      openWhenHidden: true,
      onmessage(event) {
        try {
          const data = JSON.parse(event.data) as {
            progress?: RunProgress | null;
            terminal?: boolean;
            status?: string;
          };
          if (data.progress) onProgress(data.progress);
          if (data.terminal) resolve(data.status === "failed" ? "failed" : "done");
        } catch {
          /* ignore malformed frames */
        }
      },
      onerror(err) {
        throw err; // no reconnect: the poll carries the run from here
      },
    }).catch(() => {});
  });
}

/** Polls the run (backing off, honouring 429 Retry-After) until it is done or failed. */
async function pollUntilTerminal(
  runId: string,
  onProgress: (progress: RunProgress) => void,
  signal: AbortSignal
): Promise<Terminal | "timeout"> {
  let intervalMs = 1_000;
  while (!signal.aborted) {
    try {
      const { data, response } = await browserApi.GET("/v1/runs/{run_id}", {
        params: { path: { run_id: runId } },
        signal,
      });
      if (response.status === 429) {
        intervalMs = Math.max(4_000, Number(response.headers.get("retry-after")) * 1000 || 0);
      } else if (data) {
        if (data.progress) onProgress(data.progress);
        if (data.status === "done" || data.status === "failed") return data.status;
        intervalMs = Math.min(4_000, intervalMs + 250);
      }
    } catch {
      /* transient network error or abort - retry until the deadline */
    }
    await sleep(intervalMs, signal);
  }
  return "timeout";
}

/**
 * Follow a run until it finishes; returns the audit report or raises the run's error.
 * Watching uses the browser session (the Next.js proxy), also for runs started with an API key.
 */
export async function watchRun(
  runId: string,
  onProgress: (progress: RunProgress) => void,
  maxMs = DEFAULT_RUN_TIMEOUT_MS
): Promise<RunAuditDetail> {
  const stop = new AbortController();
  const signal = AbortSignal.any([stop.signal, AbortSignal.timeout(maxMs)]);
  try {
    const outcome = await Promise.race([
      streamUntilTerminal(runId, onProgress, signal),
      pollUntilTerminal(runId, onProgress, signal),
    ]);
    if (outcome === "timeout") {
      raiseRunError("Run timed out - check worker and inference logs", {
        step: "Audit worker",
        runId,
      });
    }
  } finally {
    stop.abort();
  }
  const { data: run, response } = await browserApi.GET("/v1/runs/{run_id}", {
    params: { path: { run_id: runId } },
  });
  if (!run || run.status === "failed" || !run.result) {
    raiseRunError(run?.error || `Run failed (HTTP ${response.status})`, {
      step: "Audit worker",
      runId,
    });
  }
  return run.result;
}

// --- Start a run ---

export type RunPayload = {
  documents: DocumentDef[];
  /** Builder test runs send the unsaved draft. */
  rules?: WorkflowRule[];
  filesByDocId?: Record<string, File>;
};

/**
 * Start the run with its files and follow it to the end.
 * `apiKey` runs as the deployed workflow (integrator path); otherwise the session runs a test.
 */
export async function runWorkflow(
  workflowId: string,
  payload: RunPayload,
  options: RunReporter & { apiKey?: string } = {}
): Promise<RunAuditDetail> {
  const { apiKey, ...reporter } = options;
  if (apiKey !== undefined && !isFullWorkflowApiKey(apiKey)) {
    throw new Error(
      "Full API key unavailable — copy it when you deploy, or redeploy to generate a new key."
    );
  }
  const form = new FormData();
  for (const doc of payload.documents) {
    const file = payload.filesByDocId?.[doc.id];
    if (!file) continue;
    form.append("files", file, file.name);
    form.append("documents", doc.id);
  }
  if (!apiKey && payload.rules) {
    form.append(
      "definition",
      JSON.stringify({ documents: payload.documents, rules: payload.rules })
    );
  }

  report(reporter, "start-run");
  const response = await fetch(`/api/v1/workflows/${encodeURIComponent(workflowId)}/runs`, {
    method: "POST",
    headers: apiKey ? (workflowAuthHeaders(apiKey) as Record<string, string>) : undefined,
    body: form,
    signal: AbortSignal.timeout(120_000),
  });
  if (!response.ok) {
    raiseRunError(formatApiError(await response.text()) || `HTTP ${response.status}`, {
      step: "Start audit run",
      status: response.status,
    });
  }
  const { runId } = (await response.json()) as { runId: string };

  report(reporter, "poll-run");
  const client = reporter.clientLabels ? clientProgress(reporter.clientLabels, "poll-run") : null;
  return watchRun(runId, (progress) =>
    reporter.onProgress?.(client ? withWorkerSteps(client, progress) : progress)
  );
}
