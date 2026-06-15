import * as Sentry from "@sentry/nextjs";

export async function register() {
  if (process.env.NEXT_RUNTIME === "nodejs") {
    await import("./bugsink.server.config");
  }

  if (process.env.NEXT_RUNTIME === "edge") {
    await import("./bugsink.edge.config");
  }
}

export const onRequestError = Sentry.captureRequestError;
