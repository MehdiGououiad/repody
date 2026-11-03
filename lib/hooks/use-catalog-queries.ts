"use client";

import { useQuery } from "@tanstack/react-query";
import { browserApi, throwOnApiError } from "@/lib/api/openapi-client";
import type { ModelsCatalogResponse } from "@/lib/api/schema-types";
import { queryKeys } from "@/lib/hooks/query-keys";
import type { RuleTemplate } from "@/lib/types";

const CATALOG_STALE_MS = 5 * 60_000;

async function fetchModelsCatalog(): Promise<ModelsCatalogResponse> {
  const { data, error, response } = await browserApi.GET("/v1/models/catalog");
  if (error || !response.ok || !data) throwOnApiError(error, response);
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
      const { data, error, response } = await browserApi.GET("/v1/rules/library");
      if (error || !response.ok || !data) throwOnApiError(error, response);
      const body = data as { rules: RuleTemplate[] };
      return body.rules;
    },
    staleTime: CATALOG_STALE_MS,
  });
}
