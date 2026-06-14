import { cache } from "react";
import { browserJson, serverJson } from "@/lib/api/openapi-client";

export interface DocumentModelSummary {
  id: string;
  label: string;
  runtime: string;
  runtimeModel: string;
}

export interface PlatformConfig {
  appName: string;
  extractor: string;
  inferenceMode: string;
  storageBackend: string;
  queueBackend: string;
  runJobsInline: boolean;
  directUploadEnabled: boolean;
  cacheEnabled: boolean;
  rateLimitEnabled: boolean;
  structuredLlm: boolean;
  defaultOcrModel: string;
  defaultReadPath: string;
  documentModels: DocumentModelSummary[];
  ocrMaxPages: number;
  dockerModelRunnerBaseUrl: string;
  vllmBaseUrl: string;
  maxUploadBytes: number;
  maxUploadFiles: number;
  staleRunTimeoutMinutes: number;
  queuedStaleTimeoutMinutes: number;
  hatchetTaskTimeoutMinutes: number;
  maintenanceIntervalSeconds: number;
  workerPools: Record<string, string>;
  hatchetConfigured: boolean;
  llmValidationEnabled: boolean;
  gpuLiveProbe: boolean;
  healthzProbeInference: boolean;
}

export async function fetchPlatformConfig(): Promise<PlatformConfig> {
  return browserJson<PlatformConfig>("/platform/config");
}

/** Server Components — per-request cached platform config. */
export const fetchPlatformConfigServer = cache(async (): Promise<PlatformConfig> => {
  return serverJson<PlatformConfig>("/platform/config");
});

export function formatBytes(bytes: number): string {
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
