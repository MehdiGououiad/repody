import * as Sentry from "@sentry/nextjs";

// Every route, and the proxy, runs on Node.js (Next 16): no edge configuration to load.
export async function register() {
  if (process.env.NEXT_RUNTIME === "nodejs") {
    // A response proxied to the API (proxy.ts rewrites /api/v1/*) gets up to 10 `close`
    // listeners from Next.js itself (its router, request abort controllers and rewrite proxy),
    // and 1 from Sentry's request isolation: one past Node's default of 10, so Node warned
    // "MaxListenersExceededWarning" on such requests. They are bounded per response and removed
    // when it closes, not a leak; Node's documented remedy is a higher limit
    // (https://nodejs.org/api/events.html#eventsdefaultmaxlisteners). 20 still flags a real leak.
    const { EventEmitter } = await import("node:events");
    EventEmitter.defaultMaxListeners = 20;
    await import("./bugsink.server.config");
  }
}

export const onRequestError = Sentry.captureRequestError;
