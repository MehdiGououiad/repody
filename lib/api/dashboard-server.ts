import "server-only";

import { cache } from "react";
import {
  type DashboardBundle,
  dashboardSnapshotFromResponse,
  EMPTY_DASHBOARD_QUEUE,
} from "@/lib/api/dashboard";
import { throwOnApiError } from "@/lib/api/openapi-client";
import { serverApi } from "@/lib/api/openapi-server";

export const fetchDashboardBundle = cache(async (): Promise<DashboardBundle> => {
  try {
    const { data, error, response } = await serverApi.GET("/v1/dashboard");
    if (error || !response.ok || !data) throwOnApiError(error, response);
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
