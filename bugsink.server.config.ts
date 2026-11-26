import * as Sentry from "@sentry/nextjs";

import { bugsinkSdkOptions } from "./lib/bugsink-sdk-options";

Sentry.init({
  ...bugsinkSdkOptions(process.env.BUGSINK_DSN),
  // No request sessions: Bugsink stores errors only, and tracking them adds two `close` listeners
  // to every response, which with Next's own rewrite proxy (/api/v1) passes Node's limit of 10
  // and logs a MaxListenersExceededWarning. An integration replaces the default of its name.
  integrations: [Sentry.httpIntegration({ sessions: false })],
});
