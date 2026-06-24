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
  return catalog.models.filter(
    (model) => model.kind === "document_model" || model.markdownOnly === true,
  );
}

/** Document + OCR-compare models for operator benchmarks. */
export function benchmarkModelsFromCatalog(catalog: ModelsCatalogResponse) {
  return catalog.models.filter(
    (model) => model.kind === "document_model" || model.kind === "ocr_compare",
  );
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

export type ModelRuntimeConfigResponse = {
  models: Array<{
    modelId: string;
    label: string;
    runtime: string;
    runtimeModel: string;
    enabled: boolean;
    compareOnly?: boolean;
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
    queryKey: ["catalog", "model-runtime-config"],
    enabled,
    queryFn: async (): Promise<ModelRuntimeConfigResponse> => {
      const response = await fetch("/api/v1/platform/model-runtime-config", {
        credentials: "include",
      });
      if (!response.ok) {
        throw new Error(await response.text());
      }
      return (await response.json()) as ModelRuntimeConfigResponse;
    },
    staleTime: CATALOG_STALE_MS,
  });
}
