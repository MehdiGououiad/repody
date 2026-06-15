import type { Workflow } from "@/lib/types";
import type { Audit, HealthAlert, KpiMetric, PerformancePoint, ViolationBreakdown } from "@/lib/types";
import type { PlatformConfig } from "@/lib/api/platform-config";
import { fetchPlatformConfigServer } from "@/lib/api/platform-config";
import type { BenchmarkReport, OperatorJob, OperatorStatus } from "@/lib/api/operator";
import { serverApi, throwOnApiError } from "@/lib/api/openapi-client";
import { serverJson } from "@/lib/api/http";
import { fetchAudits, fetchMetrics, fetchWorkflows } from "@/lib/api/client";

export type PlatformHealth = {
  status: string;
  extractor: string;
  inference: string;
  modelRunner?: boolean | null;
  storageBackend?: string;
  cacheEnabled: boolean;
  queueBackend: string;
  queuedRuns: number;
  inflightRuns: number;
  hatchetConfigured: boolean;
  workerPools: Record<string, string>;
  rateLimitEnabled?: boolean;
  admissionControlEnabled?: boolean;
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
  healthz: PlatformHealth | null;
  platform: PlatformConfig | null;
  operatorStatus: OperatorStatus | null;
  operatorJobs: OperatorJob[];
  benchmark: BenchmarkReport | null;
  ocr: OcrDiagnostic | null;
};

async function fetchHealthzServer(): Promise<PlatformHealth | null> {
  try {
    return await serverJson<PlatformHealth>("/healthz");
  } catch {
    return null;
  }
}

async function fetchOcrDiagnosticServer(): Promise<OcrDiagnostic | null> {
  try {
    return await serverJson<OcrDiagnostic>("/diagnostics/ocr");
  } catch {
    return null;
  }
}

async function fetchOperatorStatusServer(): Promise<OperatorStatus | null> {
  try {
    const { data, error, response } = await serverApi.GET("/v1/operator/status");
    if (error || !response.ok || !data) throwOnApiError(error, response);
    return data as OperatorStatus;
  } catch {
    return null;
  }
}

async function fetchOperatorJobsServer(): Promise<OperatorJob[]> {
  try {
    const { data, error, response } = await serverApi.GET("/v1/operator/jobs");
    if (error || !response.ok || !data) throwOnApiError(error, response);
    return (data as { jobs: OperatorJob[] }).jobs;
  } catch {
    return [];
  }
}

async function fetchLatestBenchmarkServer(): Promise<BenchmarkReport | null> {
  try {
    const { data, error, response } = await serverApi.GET("/v1/operator/benchmarks/latest");
    if (error || !response.ok || !data) return null;
    return data as BenchmarkReport;
  } catch {
    return null;
  }
}

export async function fetchDashboardBundle(): Promise<DashboardBundle> {
  const [
    metricsResult,
    auditsResult,
    workflowsResult,
    platformResult,
    healthzResult,
    operatorStatusResult,
    operatorJobsResult,
    benchmarkResult,
    ocrResult,
  ] = await Promise.allSettled([
    fetchMetrics(),
    fetchAudits(),
    fetchWorkflows(),
    fetchPlatformConfigServer(),
    fetchHealthzServer(),
    fetchOperatorStatusServer(),
    fetchOperatorJobsServer(),
    fetchLatestBenchmarkServer(),
    fetchOcrDiagnosticServer(),
  ]);

  const metrics = metricsResult.status === "fulfilled" ? metricsResult.value : null;
  const audits =
    auditsResult.status === "fulfilled" ? auditsResult.value.audits : [];
  const workflows =
    workflowsResult.status === "fulfilled" ? workflowsResult.value : [];
  const platform =
    platformResult.status === "fulfilled" ? platformResult.value : null;
  const healthz =
    healthzResult.status === "fulfilled" ? healthzResult.value : null;
  const operatorStatus =
    operatorStatusResult.status === "fulfilled" ? operatorStatusResult.value : null;
  const operatorJobs =
    operatorJobsResult.status === "fulfilled" ? operatorJobsResult.value : [];
  const benchmark =
    benchmarkResult.status === "fulfilled" ? benchmarkResult.value : null;
  const ocr = ocrResult.status === "fulfilled" ? ocrResult.value : null;

  const apiLive = metrics !== null;

  return {
    apiLive,
    kpis: metrics?.kpis ?? [],
    performanceSeries: metrics?.performanceSeries ?? [],
    violationBreakdown: metrics?.violationBreakdown ?? [],
    healthAlerts: metrics?.healthAlerts ?? [],
    audits,
    workflows,
    healthz,
    platform,
    operatorStatus,
    operatorJobs,
    benchmark,
    ocr,
  };
}
