import type { DocumentDef, WorkflowRule } from "@/lib/types";
import { humanizeRunError } from "@/lib/api/api-error";
import {
  buildClientProgress,
  mergeServerProgress,
  type ClientStepLabels,
} from "@/lib/api/client-run-progress";
import { waitForRunUntilDone, type RunProgress } from "@/lib/api/run-poll";
import {
  fetchWithTimeout,
  getUploadCapabilities,
  raiseStepError,
  reportClientStep,
  type ProgressReporter,
  type StoredUploadBinding,
  uploadViaPresign,
} from "@/lib/api/run-upload";
import type { RunAuditDetail } from "@/lib/types/audit";
import { isFullWorkflowApiKey } from "@/lib/api/workflow-api-key";

export type { RunProgress, RunProgressStep } from "@/lib/api/run-poll";
export type TestRunResult = RunAuditDetail & { processedAt?: string };

function buildSnapshot(payload: {
  documents: DocumentDef[];
  rules: WorkflowRule[];
  workflowName: string;
}) {
  return {
    documents: payload.documents,
    rules: payload.rules,
    workflowName: payload.workflowName,
  };
}

async function startTestRun(
  workflowId: string,
  snapshot: ReturnType<typeof buildSnapshot>,
  options?: { inline?: boolean; fileBindings?: StoredUploadBinding[] }
): Promise<{ runId: string } | RunAuditDetail> {
  const inline = options?.inline ?? false;
  const qs = new URLSearchParams({ mode: "test" });
  if (inline) qs.set("inline", "true");

  const body: Record<string, unknown> = { snapshot };
  if (options?.fileBindings?.length) {
    body.fileBindings = options.fileBindings.map((b) => ({
      documentId: b.documentId,
      storageKey: b.storageKey,
      mimeType: b.mimeType,
      fileName: b.fileName,
    }));
  }

  const res = await fetchWithTimeout(`/api/workflows/${workflowId}/runs/json?${qs}`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
    timeoutMs: 60_000,
  });
  if (!res.ok) {
    const text = await res.text();
    raiseStepError("Start audit run", text || `HTTP ${res.status}`, res.status);
  }
  const payload = await res.json();
  if (inline && payload.result) {
    return payload.result as RunAuditDetail;
  }
  return { runId: payload.runId as string };
}

function makeProgressHandler(reporter?: ProgressReporter) {
  const clientSnapshot =
    reporter?.clientLabels && reporter.onProgress
      ? buildClientProgress(reporter.clientLabels, "poll-run")
      : null;
  return (serverProgress: RunProgress) => {
    if (!reporter?.onProgress) return;
    if (clientSnapshot) {
      reporter.onProgress(mergeServerProgress(clientSnapshot, serverProgress));
    } else {
      reporter.onProgress(serverProgress);
    }
  };
}

async function waitForRun(runId: string, reporter?: ProgressReporter) {
  reportClientStep(reporter, "poll-run");
  const detail = await waitForRunUntilDone(runId, makeProgressHandler(reporter));
  return { ...detail, processedAt: detail.createdAt };
}

/** Inline test run (schema/stub path, fast). Does not mutate saved workflow. */
export async function runTestInline(
  workflowId: string,
  payload: {
    documents: DocumentDef[];
    rules: WorkflowRule[];
    workflowName: string;
  },
  reporter?: ProgressReporter
): Promise<TestRunResult> {
  const snapshot = buildSnapshot(payload);
  reportClientStep(reporter, "start-run");
  const result = await startTestRun(workflowId, snapshot, { inline: true });
  if ("runId" in result) {
    return waitForRun(result.runId, reporter);
  }
  return { ...result, processedAt: result.createdAt };
}

/** Upload PDFs/images and run extraction via worker (SSE with poll fallback). */
export async function runTestWithFiles(
  workflowId: string,
  payload: {
    documents: DocumentDef[];
    rules: WorkflowRule[];
    workflowName: string;
    filesByDocId: Record<string, File>;
  },
  reporter?: ProgressReporter
): Promise<TestRunResult> {
  const docOrder = payload.documents
    .filter((d) => d.documentType.trim() && payload.filesByDocId[d.id])
    .map((d) => d.id);

  const snapshot = buildSnapshot(payload);

  const caps = await getUploadCapabilities();
  if (caps.directUploadEnabled && caps.uploadMode === "presigned" && docOrder.length > 0) {
    try {
      const bindings = await uploadViaPresign(docOrder, payload.filesByDocId, reporter);
      reportClientStep(reporter, "start-run");
      const start = await startTestRun(workflowId, snapshot, { fileBindings: bindings });
      if (!("runId" in start)) {
        return { ...start, processedAt: start.createdAt };
      }
      return waitForRun(start.runId, reporter);
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      const canFallback =
        message === "presign_unavailable" ||
        message.startsWith("Direct upload failed") ||
        message.includes("HTTP 403") ||
        humanizeRunError(message).includes("HTTP 403") ||
        message.startsWith("Prepare upload failed") ||
        message.startsWith("Confirm upload failed") ||
        message.includes("timed out");
      if (!canFallback) {
        throw err;
      }
      reportClientStep(
        reporter,
        "upload-transfer",
        reporter?.clientLabels?.["upload-check"].pendingDetail ??
          "Direct upload unavailable — sending files through API…"
      );
    }
  }

  reportClientStep(reporter, "upload-transfer", "Uploading via API…");
  const form = new FormData();
  form.append("payload", JSON.stringify(snapshot));
  form.append("document_ids", JSON.stringify(docOrder));
  for (const docId of docOrder) {
    form.append("files", payload.filesByDocId[docId]);
  }

  reportClientStep(reporter, "start-run");
  const startRes = await fetchWithTimeout(`/api/workflows/${workflowId}/runs?mode=test`, {
    method: "POST",
    body: form,
    timeoutMs: 120_000,
  });
  if (!startRes.ok) {
    const text = await startRes.text();
    raiseStepError("Start audit run", text || `HTTP ${startRes.status}`, startRes.status);
  }
  const { runId } = (await startRes.json()) as { runId: string };
  return waitForRun(runId, reporter);
}

/** Deployed API run with optional file upload (SSE with poll fallback). */
export async function runWorkflowApi(
  workflowId: string,
  apiKey: string,
  file?: File,
  onProgress?: (progress: RunProgress) => void
) {
  if (!isFullWorkflowApiKey(apiKey)) {
    throw new Error(
      "Full API key unavailable — copy it when you deploy, or redeploy to generate a new key."
    );
  }

  const form = new FormData();
  if (file) form.append("files", file);

  const start = await fetchWithTimeout(`/api/v1/workflows/${workflowId}/runs`, {
    method: "POST",
    headers: { Authorization: `Bearer ${apiKey}` },
    body: form,
    timeoutMs: 120_000,
  });
  if (!start.ok) {
    const text = await start.text();
    raiseStepError("Start API run", text || `HTTP ${start.status}`, start.status);
  }
  const { runId } = (await start.json()) as { runId: string };
  return waitForRunUntilDone(runId, onProgress);
}

export type { ClientStepLabels };
