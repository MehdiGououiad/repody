import "server-only";

import { cache } from "react";
import { throwOnApiError } from "@/lib/api/openapi-client";
import { serverApi } from "@/lib/api/openapi-server";
import {
  normalizePlatformConfig,
  type PlatformConfig,
} from "@/lib/api/platform-config";

/** Server Components — per-request cached platform config. */
export const fetchPlatformConfigServer = cache(
  async (): Promise<PlatformConfig> => {
    const { data, error, response } = await serverApi.GET("/v1/platform/config");
    if (error || !response.ok || !data) throwOnApiError(error, response);
    return normalizePlatformConfig(data);
  }
);
