"use client";

import { useQuery } from "@tanstack/react-query";
import { browserApi, unwrap } from "@/lib/api/openapi-client";
import { queryKeys } from "@/lib/hooks/query-keys";

/** Platform configuration, including whether the llama-server serves the model. */
export function usePlatformConfig() {
  return useQuery({
    queryKey: queryKeys.platformConfig,
    queryFn: () => unwrap(browserApi.GET("/v1/platform/config")),
    staleTime: 60_000,
  });
}
