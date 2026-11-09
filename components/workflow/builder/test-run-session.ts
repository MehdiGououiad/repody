import type { UploadedFile } from "@/components/workflow/ingestion-section";
import type { RunProgress } from "@/lib/api/run";
import type { RunAuditDetail } from "@/lib/types";

/**
 * A builder test run, one phase at a time with only the data that phase has:
 *
 *   idle ──run──▶ running ──▶ done | failed ──run again──▶ running
 *
 * See docs/LIFECYCLES.md.
 */
export type TestRun =
  | { phase: "idle" }
  | { phase: "running"; progress: RunProgress | null }
  | { phase: "done"; result: RunAuditDetail }
  | { phase: "failed"; error: string; runId: string | null };

/** The test files stay chosen across runs; the run itself is a `TestRun`. */
export interface TestSessionState {
  run: TestRun;
  filesByDocId: Record<string, File>;
  uploadMeta: Record<string, UploadedFile | null>;
}

export const emptyTestSession = (): TestSessionState => ({
  run: { phase: "idle" },
  filesByDocId: {},
  uploadMeta: {},
});

/** Progress only updates a run that is still running (a late event never reopens a result). */
export function withProgress(run: TestRun, progress: RunProgress): TestRun {
  return run.phase === "running" ? { phase: "running", progress } : run;
}

export function formatUploadSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
