"use client";

/**
 * One workflow run from the browser: post the files (multipart) to start it, then poll
 * `GET /v1/runs/{id}` until it is done or failed. The server owns the run's timeout, and its
 * maintenance fails runs whose worker was lost, so polling always ends.
 */
import { useMutation } from "@tanstack/react-query";
import { ApiError, apiErrorMessage } from "@/lib/api/api-error";
import { $api } from "@/lib/api/browser";
import type { paths } from "@/lib/api/generated/schema";
import { isFullWorkflowApiKey } from "@/lib/api/workflow-api-key";
import { openCredits } from "@/lib/credits/dialog";
import type { DocumentDef, RunAuditDetail, RunProgress, WorkflowRule } from "@/lib/types";

const POLL_MS = 1_000;
const WAKE_COOLDOWN_MS = 60_000;
const WAKE_PATH: keyof paths = "/v1/model/wake";

let lastWakeAt = -Infinity;

export function wakeModel(): void {
  const now = Date.now();
  if (now - lastWakeAt < WAKE_COOLDOWN_MS) return;
  lastWakeAt = now;
  void fetch(`/api${WAKE_PATH}`, { method: "POST" }).catch(() => undefined);
}


export type StartRun = {
  workflowId: string;
  documents: DocumentDef[];
  files: Record<string, File>;
  /** Builder test runs send the unsaved draft; API runs use the deployed workflow. */
  rules?: WorkflowRule[];
  /** Run as the deployed workflow (the integrator path); otherwise as the signed-in user. */
  apiKey?: string;
};

export async function startRun({ workflowId, documents, files, rules, apiKey }: StartRun) {
  if (apiKey !== undefined && !isFullWorkflowApiKey(apiKey)) {
    throw new Error("The full API key is shown once, on deploy: redeploy for a new one.");
  }
  const form = new FormData();
  for (const doc of documents) {
    const file = files[doc.id];
    if (!file) continue;
    form.append("files", file, file.name);
    form.append("documents", doc.id);
  }
  if (!apiKey && rules) form.append("definition", JSON.stringify({ documents, rules }));
  const response = await fetch(`/api/v1/workflows/${encodeURIComponent(workflowId)}/runs`, {
    method: "POST",
    headers: apiKey ? { Authorization: `Bearer ${apiKey}` } : undefined,
    body: form,
    signal: AbortSignal.timeout(120_000),
  });
  if (!response.ok) {
    // Not browserFetch: its 403 would leave the page, and a bad API key's 401 is not the
    // session's. The account out of credits (402) still opens the credits dialog.
    if (response.status === 402) openCredits();
    const message = apiErrorMessage(await response.text()) || `HTTP ${response.status}`;
    throw new ApiError(message, response.status);
  }
  return (await response.json()) as { runId: string };
}

/** Start a run; `data.runId` is the run to follow with `useRun`. */
export function useStartRun() {
  return useMutation({ mutationFn: startRun });
}

export type RunView =
  | { phase: "idle" }
  | { phase: "running"; progress: RunProgress | null }
  | { phase: "done"; result: RunAuditDetail }
  | { phase: "failed"; error: string };

/** The run's state, polled every second until it is done or failed, or cannot be read (a
 * deleted or expired run would otherwise be polled for as long as the page is open). */
export function useRun(runId: string | null): RunView {
  const { data, error } = $api.useQuery(
    "get",
    "/v1/runs/{run_id}",
    { params: { path: { run_id: runId ?? "" } } },
    {
      enabled: runId !== null,
      staleTime: 0,
      refetchInterval: (query) => {
        const status = query.state.data?.status;
        if (query.state.error || status === "done" || status === "failed") return false;
        return POLL_MS;
      },
    }
  );
  if (runId === null) return { phase: "idle" };
  if (error)
    return { phase: "failed", error: apiErrorMessage(error) || "The run could not be read." };
  if (data?.status === "done" && data.result) return { phase: "done", result: data.result };
  if (data?.status === "failed") return { phase: "failed", error: data.error ?? "The run failed." };
  return { phase: "running", progress: data?.progress ?? null };
}
