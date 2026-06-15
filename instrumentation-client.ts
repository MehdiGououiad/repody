import * as Sentry from "@sentry/nextjs";

import { bugsinkSdkOptions } from "./lib/bugsink-sdk-options";

Sentry.init(bugsinkSdkOptions(process.env.NEXT_PUBLIC_BUGSINK_DSN));
