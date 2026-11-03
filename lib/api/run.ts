/**
 * One workflow run from the browser: upload files (presigned PUT to S3), start the run,
 * then follow it to the end. Progress comes from SSE, with a status poll that keeps the
 * queue position fresh and finishes the run if the stream drops.
 */
import { fetchEventSource } from "@microsoft/fetch-event-source";
import { formatApiError, raiseRunError } from "@/lib/api/api-error";
import { workflowAuthHeaders } from "@/lib/api/auth-policy";
import { fetchWithTimeout } from "@/lib/api/fetch-with-timeout";
import { browserApi } from "@/lib/api/openapi-client";
import { isFullWorkflowApiKey } from "@/lib/api/workflow-api-key";
import type { DocumentDef, WorkflowRule } from "@/lib/types";
import type { RunAuditDetail } from "@/lib/types/audit";

// --- Progress model shown by RunProgressSteps (client steps + worker steps) ---

export type RunProgressStep = {
  id: string;
  label: string;
  status: "pending" | "active" | "done";
  mode?: "document_model";
  kind?: "logic";
  detail?: string;
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

const CLIENT_STEPS = [
  "save-workflow",
  "upload-check",
  "upload-reuse",
  "upload-presign",
  "upload-transfer",
  "upload-confirm",
  "start-run",
  "poll-run",
] as const;

export type ClientStepId = (typeof CLIENT_STEPS)[number];
export type ClientStepLabels = Record<ClientStepId, { label: string; pendingDetail?: string }>;

/** Client-side steps with `activeId` live: earlier steps done, later ones pending. */
export function clientProgress(
  labels: ClientStepLabels,
  activeId: ClientStepId,
  detail?: string
): RunProgress {
  const activeIndex = CLIENT_STEPS.indexOf(activeId);
  const steps = CLIENT_STEPS.map((id, index): RunProgressStep => {
    const status = index < activeIndex ? "done" : index === activeIndex ? "active" : "pending";
    const row = labels[id];
    return {
      id,
      label: row.label,
      status,
      detail:
        status === "active"
          ? (detail ?? row.pendingDetail)
          : status === "pending"
            ? row.pendingDetail
            : undefined,
    };
  });
  return { currentIndex: activeIndex, label: labels[activeId].label, steps };
}

/** Client steps (all done) followed by the worker's own step plan. */
function withWorkerSteps(client: RunProgress, worker: RunProgress): RunProgress {
  const steps: RunProgressStep[] = [
    ...client.steps.map((step) => ({ ...step, status: "done" as const })),
    ...worker.steps.map((step) => ({ ...step, id: `worker-${step.id}` })),
  ];
  const active = steps.findIndex((step) => step.status === "active");
  return {
    currentIndex: active >= 0 ? active : steps.length - 1,
    label: worker.label || client.label,
    queuePosition: worker.queuePosition,
    queueDepth: worker.queueDepth,
    steps,
  };
}

export type RunReporter = {
  clientLabels?: ClientStepLabels;
  onProgress?: (progress: RunProgress) => void;
};

function report(reporter: RunReporter | undefined, stepId: ClientStepId, detail?: string) {
  if (reporter?.clientLabels && reporter.onProgress) {
    reporter.onProgress(clientProgress(reporter.clientLabels, stepId, detail));
  }
}

/** Await an openapi-fetch call; on failure raise a run error naming the step. */
async function step<T>(
  name: string,
  request: Promise<{ data?: T; error?: unknown; response: Response }>
): Promise<T> {
  const { data, error, response } = await request;
  if (!response.ok || data === undefined) {
    const text = typeof error === "string" ? error : error != null ? JSON.stringify(error) : "";
    raiseRunError(formatApiError(text) || `HTTP ${response.status}`, {
      step: name,
      status: response.status,
    });
  }
  return data;
}

// --- Upload ---

export type UploadBinding = {
  documentId: string;
  storageKey: string;
  mimeType: string;
  fileName: string;
};

/** Files already in storage for this tab, keyed by document id (same File object = reuse). */
const uploaded = new Map<string, { file: File; binding: UploadBinding }>();

const SIGNATURES: Array<[mime: string, bytes: number[], offset?: number]> = [
  ["image/jpeg", [0xff, 0xd8, 0xff]],
  ["image/png", [0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]],
  ["application/pdf", [0x25, 0x50, 0x44, 0x46]],
  ["image/webp", [0x57, 0x45, 0x42, 0x50], 8], // "WEBP" after the RIFF header
];

/** Browser `File.type` is often wrong (JPEG bytes named `.png`): trust the magic bytes first. */
async function uploadMimeType(file: File): Promise<string> {
  const head = new Uint8Array(await file.slice(0, 16).arrayBuffer());
  for (const [mime, bytes, offset = 0] of SIGNATURES) {
    if (bytes.every((byte, i) => head[offset + i] === byte)) return mime;
  }
  const declared = (file.type || "").split(";", 1)[0].trim().toLowerCase();
  return declared === "image/jpg" ? "image/jpeg" : declared || "application/octet-stream";
}

async function uploadFiles(
  docIds: string[],
  files: Record<string, File>,
  reporter?: RunReporter
): Promise<UploadBinding[]> {
  report(reporter, "upload-check");
  for (const id of uploaded.keys()) if (!docIds.includes(id)) uploaded.delete(id);
  if (docIds.every((id) => uploaded.get(id)?.file === files[id])) {
    const reused = docIds.map((id) => uploaded.get(id)?.binding as UploadBinding);
    const names = reused.map((b) => b.fileName).join(", ");
    const template = reporter?.clientLabels?.["upload-reuse"].pendingDetail;
    report(reporter, "start-run", template?.replace("{files}", names) ?? `Reusing: ${names}`);
    return reused;
  }

  report(reporter, "upload-presign");
  const presign = await step(
    "Prepare upload",
    browserApi.POST("/v1/uploads/presign", {
      body: {
        files: await Promise.all(
          docIds.map(async (documentId) => ({
            fileName: files[documentId].name,
            mimeType: await uploadMimeType(files[documentId]),
            size: files[documentId].size,
            documentId,
          }))
        ),
      },
    })
  );
  if (presign.uploadMode !== "presigned") {
    raiseRunError("Direct uploads to storage are disabled (AUDIT_DIRECT_UPLOAD_ENABLED).", {
      step: "Prepare upload",
      status: 503,
    });
  }

  for (const item of presign.uploads) {
    const file = files[item.documentId ?? ""];
    if (!file || !item.uploadUrl) raiseRunError("Missing upload URL", { step: "Upload file" });
    report(reporter, "upload-transfer", file.name);
    const put = await fetchWithTimeout(item.uploadUrl, {
      method: item.method ?? "PUT",
      headers: item.headers ?? { "Content-Type": item.mimeType },
      body: file,
      timeoutMs: Math.max(120_000, Math.ceil(file.size / 40_000)),
    });
    if (!put.ok) {
      raiseRunError(`Upload of ${file.name} failed: HTTP ${put.status}`, {
        step: "Upload to storage",
        status: put.status,
      });
    }
  }

  report(reporter, "upload-confirm");
  const confirmed = await step(
    "Confirm upload",
    browserApi.POST("/v1/uploads/confirm", {
      body: { storageKeys: presign.uploads.map((u) => u.storageKey) },
    })
  );
  const refined = new Map(confirmed.uploads.map((u) => [u.storageKey, u] as const));
  return presign.uploads.map((item) => {
    const binding: UploadBinding = {
      documentId: item.documentId ?? "",
      storageKey: item.storageKey,
      mimeType: refined.get(item.storageKey)?.mimeType || item.mimeType,
      fileName: refined.get(item.storageKey)?.fileName || item.fileName,
    };
    uploaded.set(binding.documentId, { file: files[binding.documentId], binding });
    return binding;
  });
}

// --- Follow a run ---

const DEFAULT_RUN_TIMEOUT_MS = 4 * 60_000;
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
            progress?: RunProgress;
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
        throw err; // no reconnect: the status poll carries the run from here
      },
    }).catch(() => {});
  });
}

/** Polls `/runs/{id}/status` (backing off, honouring 429 Retry-After) until terminal. */
async function pollUntilTerminal(
  runId: string,
  onProgress: (progress: RunProgress) => void,
  signal: AbortSignal
): Promise<Terminal | "timeout"> {
  let intervalMs = 1_000;
  while (!signal.aborted) {
    try {
      const { data, response } = await browserApi.GET("/v1/runs/{run_id}/status", {
        params: { path: { run_id: runId } },
        signal,
      });
      if (response.status === 429) {
        intervalMs = Math.max(4_000, Number(response.headers.get("retry-after")) * 1000 || 0);
      } else if (data) {
        if (data.progress) onProgress(data.progress as RunProgress);
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
 * Follow a run until it finishes; returns the audit detail or raises the run's error.
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
  const run = await step(
    "Audit worker",
    browserApi.GET("/v1/runs/{run_id}", { params: { path: { run_id: runId } } })
  );
  if (run.status === "failed" || !run.result) {
    raiseRunError(run.error || "Run failed", { step: "Audit worker", runId });
  }
  return run.result as RunAuditDetail;
}

// --- Start a run ---

export type RunPayload = {
  documents: DocumentDef[];
  /** Builder test runs send the unsaved draft as a snapshot. */
  rules?: WorkflowRule[];
  workflowName?: string;
  filesByDocId?: Record<string, File>;
};

/**
 * Upload the files, start the run, and follow it to the end.
 * `apiKey` runs as a deployed workflow (integrator path); otherwise the session runs a test.
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
  const headers = apiKey ? (workflowAuthHeaders(apiKey) as Record<string, string>) : undefined;
  const files = payload.filesByDocId ?? {};
  const docIds = payload.documents
    .filter((doc) => doc.documentType.trim() && files[doc.id])
    .map((doc) => doc.id);
  const bindings = docIds.length ? await uploadFiles(docIds, files, reporter) : [];

  report(reporter, "start-run");
  const snapshot =
    !apiKey && payload.rules && payload.workflowName !== undefined
      ? { documents: payload.documents, rules: payload.rules, workflowName: payload.workflowName }
      : undefined;
  const { runId } = await step(
    "Start audit run",
    browserApi.POST("/v1/workflows/{workflow_id}/runs/json", {
      params: { path: { workflow_id: workflowId } },
      headers,
      body: { snapshot, fileBindings: bindings } as never,
      signal: AbortSignal.timeout(60_000),
    })
  );

  report(reporter, "poll-run");
  const client = reporter.clientLabels ? clientProgress(reporter.clientLabels, "poll-run") : null;
  return watchRun(runId, (progress) =>
    reporter.onProgress?.(client ? withWorkerSteps(client, progress) : progress)
  );
}
