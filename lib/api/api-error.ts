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

/** Turn low-level failures into actionable UI copy. */
export function humanizeRunError(raw: string, ctx?: RunErrorContext): string {
  const message = formatApiError(raw);
  const lower = message.toLowerCase();

  if (lower.includes("timed out") || lower.includes("timeout")) {
    return ctx?.step
      ? `${ctx.step} timed out. The server or worker may be busy — check Docker logs and retry.`
      : "The operation timed out. Check that the API and workers are running, then retry.";
  }
  if (lower.includes("upload not found") || lower.includes("404")) {
    return "Uploaded file was not found in storage. Try removing the file and uploading again.";
  }
  if (lower.includes("403") && lower.includes("upload")) {
    return "Direct upload to storage was rejected (HTTP 403). Retrying via API upload…";
  }
  if (lower.includes("audit queue at capacity") || lower.includes("queue at capacity")) {
    return "The platform is at capacity — too many audits are queued. Wait a minute and try again.";
  }
  if (lower.includes("stayed queued")) {
    return "The audit job never left the queue. Ensure Hatchet workers are running (`docker compose ps worker worker-fast`).";
  }
  if (lower.includes("stale running") || lower.includes("worker timeout")) {
    return "The worker stopped responding. Restart workers (`pnpm docker:restart:workers`) and run the test again.";
  }
  if (lower.includes("run timed out")) {
    return "The audit run took too long (>5 min). Check worker and Docker Model Runner logs.";
  }
  if (lower.includes("cache") && lower.includes("fail")) {
    return "Could not reuse a cached extraction result. Retry with a fresh upload or disable extraction cache.";
  }
  if (ctx?.step) {
    return `${ctx.step} failed: ${message}`;
  }
  return message || "Something went wrong. Check the platform logs and retry.";
}
