"use client";

import { useQuery } from "@tanstack/react-query";
import { browserApi, unwrap } from "@/lib/api/openapi-client";
import type { ModelsCatalogResponse } from "@/lib/api/schema-types";
import { queryKeys } from "@/lib/hooks/query-keys";
import type { RuleTemplate } from "@/lib/types";

const CATALOG_STALE_MS = 5 * 60_000;

async function fetchModelsCatalog(): Promise<ModelsCatalogResponse> {
  const data = await unwrap(browserApi.GET("/v1/models/catalog"));
  return data;
}

export function useUnifiedModelsCatalog(enabled = true) {
  return useQuery({
    queryKey: queryKeys.catalog.models,
    enabled,
    queryFn: fetchModelsCatalog,
    staleTime: CATALOG_STALE_MS,
  });
}

export function useRulesLibraryCatalog(enabled = true) {
  return useQuery({
    queryKey: queryKeys.catalog.rulesLibrary,
    enabled,
    queryFn: async (): Promise<RuleTemplate[]> => {
      const data = await unwrap(browserApi.GET("/v1/rules/library"));
      const body = data as { rules: RuleTemplate[] };
      return body.rules;
    },
    staleTime: CATALOG_STALE_MS,
  });
}
