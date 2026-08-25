"use client";

import { useQuery } from "@tanstack/react-query";
import { type DashboardSnapshot, dashboardSnapshotFromResponse } from "@/lib/api/dashboard";
import { browserApi, throwOnApiError } from "@/lib/api/openapi-client";
import type { DashboardResponse } from "@/lib/api/schema-types";
import { queryKeys } from "@/lib/hooks/query-keys";

export type LiveDashboardData = DashboardSnapshot & {
  apiLive: boolean;
  lastUpdated: Date | null;
};

const REFRESH_MS = 30_000;

type LiveSnapshot = DashboardSnapshot & { apiLive: boolean };

async function fetchDashboardLive(): Promise<LiveSnapshot> {
  const { data: body, error, response } = await browserApi.GET("/v1/dashboard");
  if (error || !response.ok || !body) throwOnApiError(error, response);
  return {
    apiLive: true,
    ...dashboardSnapshotFromResponse(body as DashboardResponse),
  };
}

export function useDashboardLive(
  initial: Omit<LiveDashboardData, "lastUpdated">
): LiveDashboardData {
  const initialSnapshot: LiveSnapshot = {
    apiLive: initial.apiLive,
    kpis: initial.kpis,
    performanceSeries: initial.performanceSeries,
    violationBreakdown: initial.violationBreakdown,
    healthAlerts: initial.healthAlerts,
    audits: initial.audits,
    workflows: initial.workflows,
    queue: initial.queue,
  };

  const query = useQuery({
    queryKey: queryKeys.dashboard.live,
    queryFn: fetchDashboardLive,
    initialData: initialSnapshot,
    // SSR already hydrated the first snapshot — skip an immediate duplicate fetch.
    staleTime: REFRESH_MS,
    refetchInterval: REFRESH_MS,
    refetchOnMount: false,
    refetchOnWindowFocus: false,
    retry: false,
  });

  const data = query.data ?? initialSnapshot;
  return {
    ...data,
    lastUpdated: data.apiLive && query.dataUpdatedAt > 0 ? new Date(query.dataUpdatedAt) : null,
  };
}
