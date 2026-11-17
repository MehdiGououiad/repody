import * as Sentry from "@sentry/nextjs";

import { bugsinkSdkOptions } from "./lib/bugsink-sdk-options";

// Errors only: Bugsink keeps no traces, so no navigation spans (onRouterTransitionStart).
Sentry.init(bugsinkSdkOptions(process.env.NEXT_PUBLIC_BUGSINK_DSN));
