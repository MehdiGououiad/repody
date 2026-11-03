import "server-only";

import { cache } from "react";
import {
  type DashboardBundle,
  dashboardSnapshotFromResponse,
  EMPTY_DASHBOARD_QUEUE,
} from "@/lib/api/dashboard";
import { unwrap } from "@/lib/api/openapi-client";
import { serverApi } from "@/lib/api/openapi-server";

export const fetchDashboardBundle = cache(async (): Promise<DashboardBundle> => {
  try {
    const data = await unwrap(serverApi.GET("/v1/dashboard"));
    return { apiLive: true, ...dashboardSnapshotFromResponse(data) };
  } catch {
    return {
      apiLive: false,
      kpis: [],
      performanceSeries: [],
      violationBreakdown: [],
      healthAlerts: [],
      audits: [],
      workflows: [],
      queue: EMPTY_DASHBOARD_QUEUE,
    };
  }
});
