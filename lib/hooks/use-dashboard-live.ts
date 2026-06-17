"use client";

import { useEffect, useState } from "react";
import { browserApi, throwOnApiError } from "@/lib/api/openapi-client";
import type { Audit, KpiMetric, PerformancePoint, ViolationBreakdown, Workflow } from "@/lib/types";

export type LiveDashboardData = {
  kpis: KpiMetric[];
  audits: Audit[];
  workflows: Workflow[];
  performanceSeries: PerformancePoint[];
  violationBreakdown: ViolationBreakdown[];
  apiLive: boolean;
  lastUpdated: Date | null;
};

const REFRESH_MS = 20_000;

export function useDashboardLive(initial: Omit<LiveDashboardData, "lastUpdated">): LiveDashboardData {
  const [data, setData] = useState<LiveDashboardData>({
    ...initial,
    lastUpdated: initial.apiLive ? new Date() : null,
  });

  useEffect(() => {
    let cancelled = false;

    async function refresh() {
      try {
        const [metricsRes, auditsRes, workflowsRes] = await Promise.all([
          browserApi.GET("/v1/metrics"),
          browserApi.GET("/v1/audits"),
          browserApi.GET("/v1/workflows"),
        ]);

        if (cancelled) return;

        if (!metricsRes.response.ok || !auditsRes.response.ok || !workflowsRes.response.ok) {
          return;
        }

        if (metricsRes.error) throwOnApiError(metricsRes.error, metricsRes.response);
        if (auditsRes.error) throwOnApiError(auditsRes.error, auditsRes.response);
        if (workflowsRes.error) throwOnApiError(workflowsRes.error, workflowsRes.response);

        const metrics = metricsRes.data as {
          kpis: KpiMetric[];
          performanceSeries: PerformancePoint[];
          violationBreakdown: ViolationBreakdown[];
        };

        setData({
          apiLive: true,
          kpis: metrics.kpis ?? [],
          performanceSeries: metrics.performanceSeries ?? [],
          violationBreakdown: metrics.violationBreakdown ?? [],
          audits: (auditsRes.data as { audits: Audit[] }).audits ?? [],
          workflows: (workflowsRes.data as { workflows: Workflow[] }).workflows ?? [],
          lastUpdated: new Date(),
        });
      } catch {
        // Keep last good snapshot when refresh fails.
      }
    }

    const id = window.setInterval(() => void refresh(), REFRESH_MS);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, []);

  return data;
}
