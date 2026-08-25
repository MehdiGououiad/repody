import type {
  Audit,
  HealthAlert,
  KpiMetric,
  PerformancePoint,
  ViolationBreakdown,
  Workflow,
} from "@/lib/types";
import type { DashboardResponse, QueueSnapshot } from "@/lib/api/schema-types";

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

export const EMPTY_DASHBOARD_QUEUE: QueueSnapshot = {
  queuedRuns: 0,
  runningRuns: 0,
  inflightRuns: 0,
};

export function dashboardSnapshotFromResponse(
  body: DashboardResponse
): DashboardSnapshot {
  const metrics = body.metrics;
  return {
    kpis: metrics.kpis as KpiMetric[],
    performanceSeries: metrics.performanceSeries as PerformancePoint[],
    violationBreakdown: metrics.violationBreakdown as ViolationBreakdown[],
    healthAlerts: (metrics.healthAlerts ?? []) as HealthAlert[],
    audits: body.audits as Audit[],
    workflows: body.workflows as Workflow[],
    queue: body.queue ?? EMPTY_DASHBOARD_QUEUE,
  };
}
