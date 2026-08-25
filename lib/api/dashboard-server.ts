import "server-only";

import { cache } from "react";
import { throwOnApiError } from "@/lib/api/openapi-client";
import { serverApi } from "@/lib/api/openapi-server";
import {
  dashboardSnapshotFromResponse,
  EMPTY_DASHBOARD_QUEUE,
  type DashboardBundle,
} from "@/lib/api/dashboard";

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
