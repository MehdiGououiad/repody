import "server-only";

import { cache } from "react";
import { unwrap } from "@/lib/api/openapi-client";
import { serverApi } from "@/lib/api/openapi-server";
import type { DashboardBundle } from "@/lib/types";

export const fetchDashboardBundle = cache(async (): Promise<DashboardBundle> => {
  try {
    return { apiLive: true, ...(await unwrap(serverApi.GET("/v1/dashboard"))) };
  } catch {
    return {
      apiLive: false,
      kpis: [],
      performanceSeries: [],
      failuresBySeverity: [],
      staleRuns: 0,
      audits: [],
      workflows: [],
      queue: { queuedRuns: 0, runningRuns: 0 },
    };
  }
});
