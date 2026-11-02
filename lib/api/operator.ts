import { browserFetch } from "@/lib/api/http";
import { browserApi, throwOnApiError } from "@/lib/api/openapi-client";
import type { Schema } from "@/lib/api/schema-types";

export type OperatorJob = Schema["OperatorJobSchema"];

export const ACTIVE_JOB_STATUSES: ReadonlySet<string> = new Set(["queued", "running"]);
export type OperatorStatus = Schema["OperatorStatusResponse"];
export type BenchmarkResult = Schema["BenchmarkResultSchema"];
export type BenchmarkReport = Schema["BenchmarkReportSchema"];

export async function fetchOperatorStatus(): Promise<OperatorStatus> {
  const { data, error, response } = await browserApi.GET("/v1/operator/status");
  if (error || !response.ok || !data) throwOnApiError(error, response);
  return data;
}

export async function fetchOperatorJobs(): Promise<OperatorJob[]> {
  const { data, error, response } = await browserApi.GET("/v1/operator/jobs");
  if (error || !response.ok || !data) throwOnApiError(error, response);
  return data.jobs;
}

export async function fetchLatestBenchmark(): Promise<BenchmarkReport | null> {
  try {
    const { data, error, response } = await browserApi.GET("/v1/operator/benchmarks/latest");
    if (error || !response.ok || !data) throwOnApiError(error, response);
    return data;
  } catch {
    return null;
  }
}

export async function fetchJobReport(jobId: string): Promise<BenchmarkReport> {
  const { data, error, response } = await browserApi.GET("/v1/operator/jobs/{job_id}/report", {
    params: { path: { job_id: jobId } },
  });
  if (error || !response.ok || !data) throwOnApiError(error, response);
  return data;
}

export async function warmupModel(model: string): Promise<OperatorJob> {
  const { data, error, response } = await browserApi.POST("/v1/operator/models/warmup", {
    body: { model },
  });
  if (error || !response.ok || !data) throwOnApiError(error, response);
  return data.job;
}

export async function startBenchmark(options: {
  profile: "quick" | "models" | "full";
  models: string[];
  validationMode: "logic_only" | "logic_and_llm";
  warmRuns: number;
  minimumAccuracy: number;
  cacheCheck: boolean;
  judgeQuality?: boolean;
  document?: File | null;
  manifest?: File | null;
}): Promise<OperatorJob> {
  const form = new FormData();
  form.set("profile", options.profile);
  form.set("models", JSON.stringify(options.models));
  form.set("validation_mode", options.validationMode);
  form.set("warm_runs", String(options.warmRuns));
  form.set("minimum_accuracy", String(options.minimumAccuracy));
  form.set("cache_check", String(options.cacheCheck));
  form.set("judge_quality", String(options.judgeQuality ?? true));
  if (options.document) form.set("document", options.document);
  if (options.manifest) form.set("manifest", options.manifest);
  // Multipart File uploads: schema types document/manifest as strings, so keep
  // thin browserFetch rather than forcing openapi-fetch body typing.
  const response = await browserFetch("/operator/benchmarks", { method: "POST", body: form });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `HTTP ${response.status}`);
  }
  const data = (await response.json()) as { job: OperatorJob };
  return data.job;
}

export function artifactUrl(jobId: string, artifact: "json" | "csv" | "html"): string {
  return `/api/operator/jobs/${jobId}/artifacts/${artifact}`;
}
