import type { components } from "@/lib/api/generated/schema";
import { browserApi, throwOnApiError } from "@/lib/api/openapi-client";

type PlatformConfigResponse = components["schemas"]["PlatformConfigResponse"];

export type PlatformConfig = PlatformConfigResponse & {
  workerPools: Record<string, string>;
};

export function normalizePlatformConfig(data: PlatformConfigResponse): PlatformConfig {
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
