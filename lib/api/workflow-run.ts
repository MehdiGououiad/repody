import type { RunProgress } from "@/lib/api/run-poll";
import {
  type ClientStepLabels,
  executeWorkflowRun,
  type WorkflowRunResult,
} from "@/lib/api/run-session";
import type { DocumentDef, WorkflowRule } from "@/lib/types";

export type { RunProgress } from "@/lib/api/run-poll";
export type { ClientStepLabels, WorkflowRunResult };

/**
 * Builder test run. Documents with an entry in `filesByDocId` go through
 * presigned upload first; the rest are evaluated inline.
 */
export async function runBuilderTest(
  workflowId: string,
  payload: {
    documents: DocumentDef[];
    rules: WorkflowRule[];
    workflowName: string;
    filesByDocId?: Record<string, File>;
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
