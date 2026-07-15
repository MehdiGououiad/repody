"use client";

import { useEffect, useState } from "react";
import { browserApi, throwOnApiError } from "@/lib/api/openapi-client";
import {
  dashboardSnapshotFromResponse,
  type DashboardSnapshot,
} from "@/lib/api/dashboard";
import type { DashboardResponse } from "@/lib/api/schema-types";

export type LiveDashboardData = DashboardSnapshot & {
  apiLive: boolean;
  lastUpdated: Date | null;
};

const REFRESH_MS = 30_000;

export function useDashboardLive(initial: Omit<LiveDashboardData, "lastUpdated">): LiveDashboardData {
  const [data, setData] = useState<LiveDashboardData>({
    ...initial,
    lastUpdated: initial.apiLive ? new Date() : null,
  });

  useEffect(() => {
    let cancelled = false;

    async function refresh() {
      try {
        const { data: body, error, response } = await browserApi.GET("/v1/dashboard");
        if (cancelled || !response.ok || !body) return;
        if (error) throwOnApiError(error, response);

        setData({
          apiLive: true,
          ...dashboardSnapshotFromResponse(body as DashboardResponse),
          lastUpdated: new Date(),
        });
      } catch {
        // Keep last good snapshot when refresh fails.
      }
    }

    // SSR already hydrated the first snapshot — skip an immediate duplicate fetch.
    const id = window.setInterval(() => void refresh(), REFRESH_MS);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, []);

  return data;
}
