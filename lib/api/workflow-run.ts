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
export type { ClientStepLabels };

/** Session JWT (builder) or deployed workflow API key (integrators). */
export type WorkflowRunCredential = "session" | { apiKey: string };

export type WorkflowRunResult = RunAuditDetail & { processedAt?: string };

type WorkflowRunPayload = {
  documents: DocumentDef[];
  rules?: WorkflowRule[];
  workflowName?: string;
  filesByDocId?: Record<string, File>;
};

type RunSnapshot = {
  documents: DocumentDef[];
  rules: WorkflowRule[];
  workflowName: string;
};

function isApiCredential(
  credential: WorkflowRunCredential
): credential is { apiKey: string } {
  return credential !== "session";
}

function buildSnapshot(payload: WorkflowRunPayload): RunSnapshot | undefined {
  if (!payload.rules || payload.workflowName === undefined) return undefined;
  return {
    documents: payload.documents,
    rules: payload.rules,
    workflowName: payload.workflowName,
  };
}

function docIdsWithFiles(payload: WorkflowRunPayload): string[] {
  if (!payload.filesByDocId) return [];
  return payload.documents
    .filter((d) => d.documentType.trim() && payload.filesByDocId![d.id])
    .map((d) => d.id);
}

function runsJsonPath(workflowId: string, credential: WorkflowRunCredential): string {
  return isApiCredential(credential)
    ? `/api/v1/workflows/${workflowId}/runs/json`
    : `/api/workflows/${workflowId}/runs/json`;
}

function runsMultipartPath(workflowId: string, credential: WorkflowRunCredential): string {
  return isApiCredential(credential)
    ? `/api/v1/workflows/${workflowId}/runs`
    : `/api/workflows/${workflowId}/runs`;
}

async function postRunJson(
  workflowId: string,
  credential: WorkflowRunCredential,
  body: { snapshot?: RunSnapshot; fileBindings?: StoredUploadBinding[] }
): Promise<{ runId: string }> {
  const payload: Record<string, unknown> = {};
  if (body.snapshot) payload.snapshot = body.snapshot;
  if (body.fileBindings?.length) {
    payload.fileBindings = body.fileBindings.map((b) => ({
      documentId: b.documentId,
      storageKey: b.storageKey,
      mimeType: b.mimeType,
      fileName: b.fileName,
    }));
  }

  const path = runsJsonPath(workflowId, credential);
  const res = isApiCredential(credential)
    ? await browserFetch(path.slice(4), {
        method: "POST",
        headers: {
          ...workflowAuthHeaders(credential.apiKey),
          "content-type": "application/json",
        },
        body: JSON.stringify(payload),
        timeoutMs: 60_000,
        workflowApiKey: credential.apiKey,
      })
    : await fetchWithTimeout(path, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(payload),
        timeoutMs: 60_000,
      });

  if (!res.ok) {
    const text = await res.text();
    raiseStepError("Start audit run", text || `HTTP ${res.status}`, res.status);
  }
  const json = (await res.json()) as { runId: string };
  return { runId: json.runId };
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

async function waitForRun(
  runId: string,
  reporter?: ProgressReporter
): Promise<WorkflowRunResult> {
  reportClientStep(reporter, "poll-run");
  const detail = await waitForRunUntilDone(runId, makeProgressHandler(reporter));
  return { ...detail, processedAt: detail.createdAt };
}

function presignFallbackAllowed(err: unknown): boolean {
  const message = err instanceof Error ? err.message : String(err);
  return (
    message === "presign_unavailable" ||
    message.startsWith("Direct upload failed") ||
    message.includes("HTTP 403") ||
    humanizeRunError(message).includes("HTTP 403") ||
    message.startsWith("Prepare upload failed") ||
    message.startsWith("Confirm upload failed") ||
    message.includes("timed out")
  );
}

async function postRunMultipart(
  workflowId: string,
  credential: WorkflowRunCredential,
  payload: WorkflowRunPayload,
  docIds: string[]
): Promise<{ runId: string }> {
  const form = new FormData();
  const snapshot = buildSnapshot(payload);
  if (snapshot) {
    form.append("payload", JSON.stringify(snapshot));
  }

  if (isApiCredential(credential)) {
    const docTypes = docIds
      .map((docId) => payload.documents.find((d) => d.id === docId)?.documentType.trim())
      .filter((name): name is string => Boolean(name));
    if (docTypes.length > 0) {
      form.append("document_types", JSON.stringify(docTypes));
    }
  } else {
    form.append("document_ids", JSON.stringify(docIds));
  }

  for (const docId of docIds) {
    const file = payload.filesByDocId![docId];
    form.append("files", file);
  }

  const path = runsMultipartPath(workflowId, credential);
  const res = isApiCredential(credential)
    ? await browserFetch(path.slice(4), {
        method: "POST",
        headers: workflowAuthHeaders(credential.apiKey),
        body: form,
        timeoutMs: 120_000,
        workflowApiKey: credential.apiKey,
      })
    : await fetchWithTimeout(path, {
        method: "POST",
        body: form,
        timeoutMs: 120_000,
      });

  if (!res.ok) {
    const text = await res.text();
    raiseStepError("Start audit run", text || `HTTP ${res.status}`, res.status);
  }
  const json = (await res.json()) as { runId: string };
  return { runId: json.runId };
}

/**
 * Start a workflow run and wait until complete.
 * Uses presigned upload + POST /runs/json when possible (fastest path).
 */
export async function runWorkflowUntilDone(
  workflowId: string,
  payload: WorkflowRunPayload,
  credential: WorkflowRunCredential,
  reporter?: ProgressReporter
): Promise<WorkflowRunResult> {
  if (isApiCredential(credential) && !isFullWorkflowApiKey(credential.apiKey)) {
    throw new Error(
      "Full API key unavailable — copy it when you deploy, or redeploy to generate a new key."
    );
  }

  const docIds = docIdsWithFiles(payload);
  const snapshot = credential === "session" ? buildSnapshot(payload) : undefined;

  if (docIds.length === 0) {
    reportClientStep(reporter, "start-run");
    const { runId } = await postRunJson(workflowId, credential, { snapshot });
    return waitForRun(runId, reporter);
  }

  const caps = await getUploadCapabilities();
  if (caps.directUploadEnabled && caps.uploadMode === "presigned") {
    try {
      const bindings = await uploadViaPresign(docIds, payload.filesByDocId!, reporter);
      reportClientStep(reporter, "start-run");
      const { runId } = await postRunJson(workflowId, credential, {
        snapshot,
        fileBindings: bindings,
      });
      return waitForRun(runId, reporter);
    } catch (err) {
      if (!presignFallbackAllowed(err)) throw err;
      reportClientStep(
        reporter,
        "upload-transfer",
        reporter?.clientLabels?.["upload-check"].pendingDetail ??
          "Direct upload unavailable — sending files through API…"
      );
    }
  }

  reportClientStep(reporter, "upload-transfer", "Uploading via API…");
  reportClientStep(reporter, "start-run");
  const { runId } = await postRunMultipart(workflowId, credential, payload, docIds);
  return waitForRun(runId, reporter);
}

/** Builder test run without file uploads. */
export async function runTestInline(
  workflowId: string,
  payload: {
    documents: DocumentDef[];
    rules: WorkflowRule[];
    workflowName: string;
  },
  reporter?: ProgressReporter
): Promise<WorkflowRunResult> {
  return runWorkflowUntilDone(workflowId, payload, "session", reporter);
}

/** Builder test run with uploaded documents. */
export async function runTestWithFiles(
  workflowId: string,
  payload: {
    documents: DocumentDef[];
    rules: WorkflowRule[];
    workflowName: string;
    filesByDocId: Record<string, File>;
  },
  reporter?: ProgressReporter
): Promise<WorkflowRunResult> {
  return runWorkflowUntilDone(workflowId, payload, "session", reporter);
}

/** Deployed workflow run from the API panel (workflow API key). */
export async function runWorkflowApi(
  workflowId: string,
  apiKey: string,
  payload: {
    documents: DocumentDef[];
    filesByDocId: Record<string, File>;
  },
  onProgress?: (progress: RunProgress) => void
): Promise<WorkflowRunResult> {
  return runWorkflowUntilDone(
    workflowId,
    payload,
    { apiKey },
    onProgress ? { onProgress } : undefined
  );
}

/** @deprecated Use WorkflowRunResult */
export type TestRunResult = WorkflowRunResult;
