/** Parse FastAPI / plain-text API errors into readable messages. */
export function formatApiError(text: string): string {
  const trimmed = text.trim();
  if (!trimmed) return "";
  try {
    const parsed = JSON.parse(trimmed) as {
      detail?: string | { msg?: string; loc?: unknown[] }[];
      error?: string;
      message?: string;
    };
    if (typeof parsed.detail === "string") return parsed.detail;
    if (Array.isArray(parsed.detail)) {
      return parsed.detail
        .map((d) => {
          if (typeof d === "string") return d;
          const msg = d.msg ?? String(d);
          const loc = Array.isArray(d.loc) ? d.loc.filter(Boolean).join(".") : "";
          return loc ? `${loc}: ${msg}` : msg;
        })
        .join("; ");
    }
    if (parsed.error) return parsed.error;
    if (parsed.message) return parsed.message;
  } catch {
    /* plain text */
  }
  return trimmed;
}

export type RunErrorContext = {
  step?: string;
  runId?: string;
  status?: number;
};

/** Thrown when a workflow run fails after a run id exists (poll / SSE path). */
export class RunWorkflowError extends Error {
  readonly runId?: string;
  readonly step?: string;

  constructor(message: string, opts?: { runId?: string; step?: string }) {
    super(message);
    this.name = "RunWorkflowError";
    this.runId = opts?.runId;
    this.step = opts?.step;
  }
}

export function raiseRunError(raw: string, ctx?: RunErrorContext): never {
  throw new RunWorkflowError(humanizeRunError(raw, ctx), {
    runId: ctx?.runId,
    step: ctx?.step,
  });
}

export function runErrorFromUnknown(err: unknown): { message: string; runId?: string } {
  if (err instanceof RunWorkflowError) {
    return { message: err.message, runId: err.runId };
  }
  const raw =
    err instanceof Error ? err.message : typeof err === "string" ? err : "Something went wrong.";
  return { message: humanizeRunError(raw) };
}

/** Turn low-level failures into actionable UI copy. */
export function humanizeRunError(raw: string, ctx?: RunErrorContext): string {
  const message = formatApiError(raw);
  const lower = message.toLowerCase();

  if (lower.includes("failed during processing")) {
    return "The audit worker could not finish this run. Check that inference is running, then retry or share the run ID below.";
  }
  if (lower.includes("run timed out")) {
    return "The audit run took too long. Check the worker and inference logs.";
  }
  if (lower.includes("timed out") || lower.includes("timeout")) {
    return ctx?.step
      ? `${ctx.step} timed out. The server or worker may be busy - retry in a moment.`
      : "The operation timed out. Check that the API and workers are running, then retry.";
  }
  if (lower.includes("upload not found")) {
    return "Uploaded file was not found in storage. Remove the file and upload it again.";
  }
  if (lower.includes("queue is full") || lower.includes("at capacity")) {
    return "The platform is at capacity. Wait a minute and try again.";
  }
  if (lower.includes("stayed queued")) {
    return "The audit job never left the queue. Check that the Taskiq workers are running.";
  }
  if (lower.includes("stale running") || lower.includes("worker timeout")) {
    return "The worker stopped responding. Restart the workers and run the test again.";
  }
  if (ctx?.step) {
    return `${ctx.step} failed: ${message}`;
  }
  return message || "Something went wrong. Check the platform logs and retry.";
}
