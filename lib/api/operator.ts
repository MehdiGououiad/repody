import { browserApi, browserFetch, browserJson, throwOnApiError } from "@/lib/api/openapi-client";
import type { InferenceModel } from "@/lib/api/inference";
import type { OcrModelOption } from "@/lib/api/ocr";

export type OperatorJob = {
  id: string;
  kind: "benchmark" | "model_pull" | "model_warmup";
  label: string;
  status: "queued" | "running" | "completed" | "failed" | "cancelled";
  createdAt: string;
  startedAt?: string | null;
  completedAt?: string | null;
  progress: string;
  output: string;
  error?: string | null;
  hasReport: boolean;
};

export type OperatorStatus = {
  actionsEnabled: boolean;
  reportDirectory: string;
  warmup: {
    documentModelOnStart: boolean;
  };
  limits: {
    maxUploadBytes: number;
    ocrMaxPages: number;
    taskTimeoutMinutes: number;
  };
};

export type BenchmarkResult = {
  case: string;
  model: string;
  phase: string;
  status: string;
  passed: boolean;
  skipped?: boolean;
  wallMs?: number | null;
  queueMs?: number | null;
  extractionMs?: number | null;
  validationMs?: number | null;
  fieldAccuracy?: number | null;
  ruleAccuracy?: number | null;
  cacheHit?: boolean | null;
  error?: string | null;
};

export type BenchmarkReport = {
  generatedAt: string;
  profile: string;
  suiteId: string;
  summary: {
    passed: number;
    failed: number;
    skipped: number;
    fieldAccuracy: number;
    ruleAccuracy: number;
    medianWallMs?: number | null;
  };
  results: BenchmarkResult[];
};

export async function fetchOperatorStatus(): Promise<OperatorStatus> {
  const { data, error, response } = await browserApi.GET("/v1/operator/status");
  if (error || !response.ok || !data) throwOnApiError(error, response);
  return data as OperatorStatus;
}

export async function fetchOperatorJobs(): Promise<OperatorJob[]> {
  const { data, error, response } = await browserApi.GET("/v1/operator/jobs");
  if (error || !response.ok || !data) throwOnApiError(error, response);
  return (data as { jobs: OperatorJob[] }).jobs;
}

export async function fetchOperatorJob(jobId: string): Promise<OperatorJob> {
  const { data, error, response } = await browserApi.GET("/v1/operator/jobs/{job_id}", {
    params: { path: { job_id: jobId } },
  });
  if (error || !response.ok || !data) throwOnApiError(error, response);
  return data as OperatorJob;
}

export async function fetchLatestBenchmark(): Promise<BenchmarkReport | null> {
  try {
    const { data, error, response } = await browserApi.GET("/v1/operator/benchmarks/latest");
    if (error || !response.ok || !data) throwOnApiError(error, response);
    return data as BenchmarkReport;
  } catch {
    return null;
  }
}

export async function fetchJobReport(jobId: string): Promise<BenchmarkReport> {
  const { data, error, response } = await browserApi.GET("/v1/operator/jobs/{job_id}/report", {
    params: { path: { job_id: jobId } },
  });
  if (error || !response.ok || !data) throwOnApiError(error, response);
  return data as BenchmarkReport;
}

export async function fetchModelCatalog(): Promise<{
  ocrModels: OcrModelOption[];
  inferenceModels: InferenceModel[];
}> {
  const [ocr, inference] = await Promise.all([
    browserJson<{ models: OcrModelOption[] }>("/ocr/models"),
    browserJson<{ models: InferenceModel[] }>("/inference/models"),
  ]);
  return { ocrModels: ocr.models, inferenceModels: inference.models };
}

export async function startModelAction(
  action: "pull" | "warmup",
  model: string
): Promise<OperatorJob> {
  const path =
    action === "pull" ? "/v1/operator/models/pull" : "/v1/operator/models/warmup";
  const { data, error, response } = await browserApi.POST(path, {
    body: { model },
  });
  if (error || !response.ok || !data) throwOnApiError(error, response);
  return (data as { job: OperatorJob }).job;
}

export async function startBenchmark(options: {
  profile: "quick" | "models" | "full";
  models: string[];
  validationMode: "logic_only" | "logic_and_llm";
  warmRuns: number;
  minimumAccuracy: number;
  cacheCheck: boolean;
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
  if (options.document) form.set("document", options.document);
  if (options.manifest) form.set("manifest", options.manifest);
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
