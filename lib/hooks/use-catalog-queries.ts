"use client";

import { useQuery } from "@tanstack/react-query";
import { browserApi, throwOnApiError } from "@/lib/api/openapi-client";
import type { ModelsCatalogResponse, PlatformConfigResponse } from "@/lib/api/schema-types";
import type { ProcessingPathsResponse } from "@/lib/api/processing-paths";
import type { RuleTemplate } from "@/lib/types";

const CATALOG_STALE_MS = 5 * 60_000;

async function fetchModelsCatalog(): Promise<ModelsCatalogResponse> {
  const { data, error, response } = await browserApi.GET("/v1/models/catalog");
  if (error || !response.ok || !data) throwOnApiError(error, response);
  return data;
}

export function documentModelsFromCatalog(catalog: ModelsCatalogResponse) {
  return catalog.models.filter((model) => model.kind === "document_model");
}

export function processingPathsFromCatalog(
  catalog: ModelsCatalogResponse,
): ProcessingPathsResponse {
  return {
    paths: catalog.paths ?? [],
    validationModes: catalog.validationModes ?? [],
    defaultPath: catalog.defaultPath ?? "document_model",
    defaultValidationMode: catalog.defaultValidationMode ?? "logic_only",
  };
}

export function useProcessingPathsCatalog() {
  return useQuery({
    queryKey: ["catalog", "processing-paths"],
    queryFn: async (): Promise<ProcessingPathsResponse> => {
      const catalog = await fetchModelsCatalog();
      return processingPathsFromCatalog(catalog);
    },
    staleTime: CATALOG_STALE_MS,
  });
}

export function useUnifiedModelsCatalog(enabled = true) {
  return useQuery({
    queryKey: ["catalog", "models-unified"],
    enabled,
    queryFn: fetchModelsCatalog,
    staleTime: CATALOG_STALE_MS,
  });
}

export function useRulesLibraryCatalog(enabled = true) {
  return useQuery({
    queryKey: ["catalog", "rules-library"],
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

export function usePlatformConfig(enabled = true) {
  return useQuery({
    queryKey: ["catalog", "platform-config"],
    enabled,
    queryFn: async (): Promise<PlatformConfigResponse> => {
      const { data, error, response } = await browserApi.GET("/v1/platform/config");
      if (error || !response.ok || !data) throwOnApiError(error, response);
      return data;
    },
    staleTime: CATALOG_STALE_MS,
  });
}
