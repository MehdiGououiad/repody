import type { Workflow } from "@/lib/types";
import type { Audit, HealthAlert, KpiMetric, PerformancePoint, ViolationBreakdown } from "@/lib/types";
import { fetchAudits, fetchMetrics, fetchWorkflows } from "@/lib/api/client";

export type PlatformHealth = {
  status: string;
  extractor: string;
  inference: string;
  queuedRuns: number;
  runningRuns: number;
  inflightRuns: number;
  hatchetConfigured: boolean;
  workerPools: Record<string, string>;
};

export type OcrDiagnostic = {
  ok: boolean;
  model: string;
  runtime: string;
  inferenceReachable: boolean;
  modelLoaded: boolean;
  detail: string;
  hint: string;
};

export type DashboardBundle = {
  apiLive: boolean;
  kpis: KpiMetric[];
  performanceSeries: PerformancePoint[];
  violationBreakdown: ViolationBreakdown[];
  healthAlerts: HealthAlert[];
  audits: Audit[];
  workflows: Workflow[];
};

export async function fetchDashboardBundle(): Promise<DashboardBundle> {
  const [metricsResult, auditsResult, workflowsResult] = await Promise.allSettled([
    fetchMetrics(),
    fetchAudits(),
    fetchWorkflows(),
  ]);

  const metrics = metricsResult.status === "fulfilled" ? metricsResult.value : null;
  const audits =
    auditsResult.status === "fulfilled" ? auditsResult.value.audits : [];
  const workflows =
    workflowsResult.status === "fulfilled" ? workflowsResult.value : [];

  const apiLive = metrics !== null;

  return {
    apiLive,
    kpis: metrics?.kpis ?? [],
    performanceSeries: metrics?.performanceSeries ?? [],
    violationBreakdown: metrics?.violationBreakdown ?? [],
    healthAlerts: metrics?.healthAlerts ?? [],
    audits,
    workflows,
  };
}
