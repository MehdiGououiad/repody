import "server-only";

import { cache } from "react";
import { type DashboardBundle, EMPTY_DASHBOARD_QUEUE } from "@/lib/api/dashboard";
import { unwrap } from "@/lib/api/openapi-client";
import { serverApi } from "@/lib/api/openapi-server";

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
      queue: EMPTY_DASHBOARD_QUEUE,
    };
  }
});
