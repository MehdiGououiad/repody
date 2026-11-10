import * as Sentry from "@sentry/nextjs";

import { bugsinkSdkOptions } from "./lib/bugsink-sdk-options";

Sentry.init(bugsinkSdkOptions(process.env.NEXT_PUBLIC_BUGSINK_DSN));

// Sentry's App Router navigation spans (official @sentry/nextjs client setup).
export const onRouterTransitionStart = Sentry.captureRouterTransitionStart;
