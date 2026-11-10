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

/** A failed API call, with its HTTP status so callers can tell "not found" from an outage. */
export class ApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}
