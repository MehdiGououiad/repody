import type { DocumentDef, WorkflowRule } from "@/lib/types";
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

/**
 * Start a workflow run and wait until complete.
 * Uses presigned upload + POST /runs/json for file-backed runs.
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
  if (!caps.directUploadEnabled || caps.uploadMode !== "presigned") {
    raiseStepError(
      "Prepare upload",
      "Direct presigned uploads are not available. Check storage configuration.",
      503
    );
  }

  const bindings = await uploadViaPresign(docIds, payload.filesByDocId!, reporter);
  reportClientStep(reporter, "start-run");
  const { runId } = await postRunJson(workflowId, credential, {
    snapshot,
    fileBindings: bindings,
  });
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
