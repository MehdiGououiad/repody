import { cache } from "react";
import type { Audit, HealthAlert, KpiMetric, PerformancePoint, ViolationBreakdown, Workflow } from "@/lib/types";
import type { DashboardResponse, QueueSnapshot } from "@/lib/api/schema-types";
import { serverApi, throwOnApiError } from "@/lib/api/openapi-client";

export type { QueueSnapshot };

export type DashboardSnapshot = {
  kpis: KpiMetric[];
  performanceSeries: PerformancePoint[];
  violationBreakdown: ViolationBreakdown[];
  healthAlerts: HealthAlert[];
  audits: Audit[];
  workflows: Workflow[];
  queue: QueueSnapshot;
};

export type DashboardBundle = DashboardSnapshot & {
  apiLive: boolean;
};

const EMPTY_QUEUE: QueueSnapshot = {
  queuedRuns: 0,
  runningRuns: 0,
  inflightRuns: 0,
};

export function dashboardSnapshotFromResponse(body: DashboardResponse): DashboardSnapshot {
  const metrics = body.metrics;
  return {
    kpis: metrics.kpis as KpiMetric[],
    performanceSeries: metrics.performanceSeries as PerformancePoint[],
    violationBreakdown: metrics.violationBreakdown as ViolationBreakdown[],
    healthAlerts: (metrics.healthAlerts ?? []) as HealthAlert[],
    audits: body.audits as Audit[],
    workflows: body.workflows as Workflow[],
    queue: body.queue ?? EMPTY_QUEUE,
  };
}

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
      queue: EMPTY_QUEUE,
    };
  }
});
