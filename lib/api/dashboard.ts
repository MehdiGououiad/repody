import type { DashboardResponse, QueueSnapshot } from "@/lib/api/schema-types";
import { workflowFromWire } from "@/lib/api/workflow-wire";
import type {
  Audit,
  HealthAlert,
  KpiMetric,
  PerformancePoint,
  ViolationBreakdown,
  Workflow,
} from "@/lib/types";

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

export function dashboardSnapshotFromResponse(body: DashboardResponse): DashboardSnapshot {
  const metrics = body.metrics;
  return {
    kpis: metrics.kpis,
    performanceSeries: metrics.performanceSeries,
    violationBreakdown: metrics.violationBreakdown,
    healthAlerts: metrics.healthAlerts ?? [],
    audits: body.audits,
    workflows: body.workflows.map(workflowFromWire),
    queue: body.queue ?? EMPTY_DASHBOARD_QUEUE,
  };
}
