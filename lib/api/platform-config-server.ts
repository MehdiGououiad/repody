import "server-only";

import { cache } from "react";
import { unwrap } from "@/lib/api/openapi-client";
import { serverApi } from "@/lib/api/openapi-server";
import { normalizePlatformConfig, type PlatformConfig } from "@/lib/api/platform-config";

/** Server Components - per-request cached platform config. */
export const fetchPlatformConfigServer = cache(async (): Promise<PlatformConfig> => {
  const data = await unwrap(serverApi.GET("/v1/platform/config"));
  return normalizePlatformConfig(data);
});
