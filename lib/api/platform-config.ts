import type { components } from "@/lib/api/generated/schema";
import { cache } from "react";
import { browserApi, serverApi, throwOnApiError } from "@/lib/api/openapi-client";

type PlatformConfigResponse = components["schemas"]["PlatformConfigResponse"];

export type PlatformConfig = PlatformConfigResponse & {
  workerPools: Record<string, string>;
};

function normalizePlatformConfig(data: PlatformConfigResponse): PlatformConfig {
  return {
    ...data,
    workerPools: data.workerPools ?? {},
  };
}

export async function fetchPlatformConfig(): Promise<PlatformConfig> {
  const { data, error, response } = await browserApi.GET("/v1/platform/config");
  if (error || !response.ok || !data) throwOnApiError(error, response);
  return normalizePlatformConfig(data);
}

/** Server Components — per-request cached platform config. */
export const fetchPlatformConfigServer = cache(async (): Promise<PlatformConfig> => {
  const { data, error, response } = await serverApi.GET("/v1/platform/config");
  if (error || !response.ok || !data) throwOnApiError(error, response);
  return normalizePlatformConfig(data);
});

export function formatBytes(bytes: number): string {
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
