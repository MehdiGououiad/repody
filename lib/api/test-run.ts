import type { DocumentDef, WorkflowRule } from "@/lib/types";
import { humanizeRunError } from "@/lib/api/api-error";
import {
  buildClientProgress,
  mergeServerProgress,
  type ClientStepLabels,
} from "@/lib/api/client-run-progress";
import { browserFetch } from "@/lib/api/http";
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
import { workflowAuthHeaders } from "@/lib/api/auth-policy";

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

async function startTestRunSession(
  workflowId: string,
  snapshot: ReturnType<typeof buildSnapshot>,
  options?: { fileBindings?: StoredUploadBinding[] }
): Promise<{ runId: string }> {
  const body: Record<string, unknown> = { ...snapshot };
  if (options?.fileBindings?.length) {
    body.fileBindings = options.fileBindings.map((b) => ({
      documentId: b.documentId,
      storageKey: b.storageKey,
      mimeType: b.mimeType,
      fileName: b.fileName,
    }));
  }

  const res = await fetchWithTimeout(`/api/workflows/${workflowId}/test-run/session`, {
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

/** Test run without uploads — async via Hatchet workers (poll until done). */
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
  const { runId } = await startTestRunSession(workflowId, snapshot);
  return waitForRun(runId, reporter);
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
      const start = await startTestRunSession(workflowId, snapshot, { fileBindings: bindings });
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
  const docTypes = docOrder
    .map((docId) => payload.documents.find((d) => d.id === docId)?.documentType.trim())
    .filter((name): name is string => Boolean(name));
  form.append("document_types", JSON.stringify(docTypes));
  for (const docId of docOrder) {
    form.append("files", payload.filesByDocId[docId]);
  }

  reportClientStep(reporter, "start-run");
  const startRes = await fetchWithTimeout(
    `/api/workflows/${workflowId}/test-run/session/upload`,
    {
      method: "POST",
      body: form,
      timeoutMs: 120_000,
    }
  );
  if (!startRes.ok) {
    const text = await startRes.text();
    raiseStepError("Start audit run", text || `HTTP ${startRes.status}`, startRes.status);
  }
  const { runId } = (await startRes.json()) as { runId: string };
  return waitForRun(runId, reporter);
}

/** Deployed API run with file uploads bound to workflow document slots. */
export async function runWorkflowApi(
  workflowId: string,
  apiKey: string,
  payload: {
    documents: DocumentDef[];
    filesByDocId: Record<string, File>;
  },
  onProgress?: (progress: RunProgress) => void
) {
  if (!isFullWorkflowApiKey(apiKey)) {
    throw new Error(
      "Full API key unavailable — copy it when you deploy, or redeploy to generate a new key."
    );
  }

  const docOrder = payload.documents
    .filter((d) => d.documentType.trim() && payload.filesByDocId[d.id])
    .map((d) => d.documentType.trim());

  const form = new FormData();
  if (docOrder.length > 0) {
    form.append("document_types", JSON.stringify(docOrder));
    for (const docId of docOrder) {
      form.append("files", payload.filesByDocId[docId]);
    }
  }

  const start = await browserFetch(`/api/v1/workflows/${workflowId}/runs`, {
    method: "POST",
    headers: workflowAuthHeaders(apiKey),
    body: form,
    timeoutMs: 120_000,
    workflowApiKey: apiKey,
  });
  if (!start.ok) {
    const text = await start.text();
    raiseStepError("Start API run", text || `HTTP ${start.status}`, start.status);
  }
  const { runId } = (await start.json()) as { runId: string };
  return waitForRunUntilDone(runId, onProgress);
}

export type { ClientStepLabels };
