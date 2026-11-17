import * as Sentry from "@sentry/nextjs";

// Every route, and the proxy, runs on Node.js (Next 16): no edge configuration to load.
export async function register() {
  if (process.env.NEXT_RUNTIME === "nodejs") {
    await import("./bugsink.server.config");
  }
}

export const onRequestError = Sentry.captureRequestError;
