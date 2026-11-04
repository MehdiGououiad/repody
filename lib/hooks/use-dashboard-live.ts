"use client";

import { useQuery } from "@tanstack/react-query";
import type { DashboardBundle } from "@/lib/api/dashboard";
import { browserApi, unwrap } from "@/lib/api/openapi-client";
import { queryKeys } from "@/lib/hooks/query-keys";

export type LiveDashboardData = DashboardBundle & { lastUpdated: Date | null };

const REFRESH_MS = 30_000;

async function fetchDashboardLive(): Promise<DashboardBundle> {
  return { apiLive: true, ...(await unwrap(browserApi.GET("/v1/dashboard"))) };
}

export function useDashboardLive(initial: DashboardBundle): LiveDashboardData {
  const query = useQuery({
    queryKey: queryKeys.dashboard.live,
    queryFn: fetchDashboardLive,
    initialData: initial,
    // SSR already hydrated the first snapshot - skip an immediate duplicate fetch.
    staleTime: REFRESH_MS,
    refetchInterval: REFRESH_MS,
    refetchOnMount: false,
    refetchOnWindowFocus: false,
    retry: false,
  });

  const data = query.data ?? initial;
  return {
    ...data,
    lastUpdated: data.apiLive && query.dataUpdatedAt > 0 ? new Date(query.dataUpdatedAt) : null,
  };
}
