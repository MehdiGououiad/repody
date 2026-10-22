import type { BrowserOptions, NodeOptions } from "@sentry/nextjs";

/** SDK options compatible with self-hosted Bugsink (no traces/sessions/client reports). */
export function bugsinkSdkOptions(dsn?: string): BrowserOptions | NodeOptions {
  const resolved = dsn?.trim();
  if (!resolved) {
    return { enabled: false };
  }

  return {
    dsn: resolved,
    environment: process.env.BUGSINK_ENVIRONMENT ?? process.env.NODE_ENV ?? "development",
    // Bugsink stores error events only and recommends PII on a self-hosted server.
    // https://www.bugsink.com/docs/sdk-recommendations/
    sendDefaultPii: true,
    tracesSampleRate: 0,
    sendClientReports: false,
  };
}
