import type { DocumentDef, WorkflowRule } from "@/lib/types";
import {
  executeWorkflowRun,
  type ClientStepLabels,
  type WorkflowRunCredential,
  type WorkflowRunResult,
} from "@/lib/api/run-session";
import type { RunProgress } from "@/lib/api/run-poll";

export type { RunProgress, RunProgressStep } from "@/lib/api/run-poll";
export type { ClientStepLabels, WorkflowRunCredential, WorkflowRunResult };

/**
 * Start a workflow run and wait until complete.
 * Uses presigned upload + POST /runs/json for file-backed runs.
 */
export async function runWorkflowUntilDone(
  workflowId: string,
  payload: {
    documents: DocumentDef[];
    rules?: WorkflowRule[];
    workflowName?: string;
    filesByDocId?: Record<string, File>;
  },
  credential: WorkflowRunCredential,
  reporter?: Parameters<typeof executeWorkflowRun>[3]
): Promise<WorkflowRunResult> {
  return executeWorkflowRun(workflowId, payload, credential, reporter);
}

/** Builder test run without file uploads. */
export async function runTestInline(
  workflowId: string,
  payload: {
    documents: DocumentDef[];
    rules: WorkflowRule[];
    workflowName: string;
  },
  reporter?: Parameters<typeof executeWorkflowRun>[3]
): Promise<WorkflowRunResult> {
  return executeWorkflowRun(workflowId, payload, "session", reporter);
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
  reporter?: Parameters<typeof executeWorkflowRun>[3]
): Promise<WorkflowRunResult> {
  return executeWorkflowRun(workflowId, payload, "session", reporter);
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
  return executeWorkflowRun(
    workflowId,
    payload,
    { apiKey },
    onProgress ? { onProgress } : undefined
  );
}
