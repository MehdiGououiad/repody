import type { UploadedFile } from "@/components/workflow/ingestion-section";
import type { RunProgress, WorkflowRunResult } from "@/lib/api/workflow-run";

export type TestPhase = "idle" | "running" | "done";

export interface TestSessionState {
  phase: TestPhase;
  progress: RunProgress | null;
  result: WorkflowRunResult | null;
  error: string | null;
  errorRunId: string | null;
  filesByDocId: Record<string, File>;
  uploadMeta: Record<string, UploadedFile | null>;
}

export const emptyTestSession = (): TestSessionState => ({
  phase: "idle",
  progress: null,
  result: null,
  error: null,
  errorRunId: null,
  filesByDocId: {},
  uploadMeta: {},
});

export function formatUploadSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
