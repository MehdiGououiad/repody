/** The message of a FastAPI error body: `{"detail": "..."}` or a list of validation errors. */
export function apiErrorMessage(body: unknown): string {
  if (typeof body === "string") {
    try {
      return apiErrorMessage(JSON.parse(body));
    } catch {
      return body.trim();
    }
  }
  const detail = (body as { detail?: unknown } | null)?.detail;
  if (typeof detail === "string") return detail;
  if (!Array.isArray(detail)) return "";
  return detail
    .map((error: { msg?: string; loc?: unknown[] }) => {
      const loc = error.loc?.filter(Boolean).join(".");
      return loc ? `${loc}: ${error.msg}` : String(error.msg);
    })
    .join("; ");
}

/** A run that failed after it started (the run id is shown so it can be looked up). */
export class RunWorkflowError extends Error {
  readonly runId?: string;

  constructor(message: string, runId?: string) {
    super(message);
    this.name = "RunWorkflowError";
    this.runId = runId;
  }
}

export function runErrorFromUnknown(error: unknown): { message: string; runId?: string } {
  if (error instanceof RunWorkflowError) return { message: error.message, runId: error.runId };
  return { message: error instanceof Error ? error.message : "Something went wrong." };
}
