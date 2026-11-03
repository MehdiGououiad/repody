import type { components } from "@/lib/api/generated/schema";

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
