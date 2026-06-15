import * as Sentry from "@sentry/nextjs";

import { bugsinkSdkOptions } from "./lib/bugsink-sdk-options";

Sentry.init(bugsinkSdkOptions(process.env.BUGSINK_DSN));
