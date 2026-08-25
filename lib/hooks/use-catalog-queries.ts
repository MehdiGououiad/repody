"use client";

import { useQuery } from "@tanstack/react-query";
import { browserApi, throwOnApiError } from "@/lib/api/openapi-client";
import type { ModelsCatalogResponse, PlatformConfigResponse } from "@/lib/api/schema-types";
import type { RuleTemplate } from "@/lib/types";
import { queryKeys } from "@/lib/hooks/query-keys";

const CATALOG_STALE_MS = 5 * 60_000;

async function fetchModelsCatalog(): Promise<ModelsCatalogResponse> {
  const { data, error, response } = await browserApi.GET("/v1/models/catalog");
  if (error || !response.ok || !data) throwOnApiError(error, response);
  return data;
}

export function documentModelsFromCatalog(catalog: ModelsCatalogResponse) {
  // Structured extraction only — markdown-only OCR engines are not selectable.
  return catalog.models.filter(
    (model) => model.kind === "document_model" && model.markdownOnly !== true,
  );
}

/** Document models for operator benchmarks. */
export function benchmarkModelsFromCatalog(catalog: ModelsCatalogResponse) {
  return catalog.models.filter((model) => model.kind === "document_model");
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

export function usePlatformConfig(enabled = true) {
  return useQuery({
    queryKey: queryKeys.catalog.platformConfig,
    enabled,
    queryFn: async (): Promise<PlatformConfigResponse> => {
      const { data, error, response } = await browserApi.GET("/v1/platform/config");
      if (error || !response.ok || !data) throwOnApiError(error, response);
      return data;
    },
    staleTime: CATALOG_STALE_MS,
  });
}

export type ModelRuntimeConfigResponse = {
  models: Array<{
    modelId: string;
    label: string;
    runtime: string;
    runtimeModel: string;
    enabled: boolean;
    inferenceUrl?: string | null;
    renderPolicy?: string;
    fields: Array<{
      key: string;
      envVar: string;
      label: string;
      description: string;
      scope: "platform" | "worker_runtime" | "inference_server";
      restart: string;
      value?: string | number | boolean | null;
      configured?: boolean;
      source?: string;
    }>;
  }>;
  shared: Array<{
    key: string;
    envVar: string;
    label: string;
    description: string;
    scope: "platform" | "worker_runtime" | "inference_server";
    restart: string;
    value?: string | number | boolean | null;
  }>;
  deploymentNotes: Array<{
    changeKind: string;
    action: string;
    detail: string;
  }>;
};

export function useModelRuntimeConfig(enabled = true) {
  return useQuery({
    queryKey: queryKeys.catalog.modelRuntimeConfig,
    enabled,
    queryFn: async (): Promise<ModelRuntimeConfigResponse> => {
      const { data, error, response } = await browserApi.GET(
        "/v1/platform/model-runtime-config",
      );
      if (error || !response.ok || !data) throwOnApiError(error, response);
      return {
        models: (data.models ?? []).map((model) => ({
          ...model,
          fields: model.fields ?? [],
        })),
        shared: data.shared ?? [],
        deploymentNotes: data.deploymentNotes ?? [],
      };
    },
    staleTime: CATALOG_STALE_MS,
  });
}
