"use client";

import { useQuery } from "@tanstack/react-query";
import { browserApi, throwOnApiError } from "@/lib/api/openapi-client";
import type { PlatformConfig } from "@/lib/api/platform-config";
import type { ModelsCatalogResponse } from "@/lib/api/models-catalog";
import type { ProcessingPathsResponse } from "@/lib/api/processing-paths";
import type { RuleTemplate } from "@/lib/types";

const CATALOG_STALE_MS = 5 * 60_000;

export function useProcessingPathsCatalog() {
  return useQuery({
    queryKey: ["catalog", "processing-paths"],
    queryFn: async (): Promise<ProcessingPathsResponse> => {
      const { data, error, response } = await browserApi.GET("/v1/processing-paths");
      if (error || !response.ok || !data) throwOnApiError(error, response);
      return data as ProcessingPathsResponse;
    },
    staleTime: CATALOG_STALE_MS,
  });
}

export function useUnifiedModelsCatalog(enabled = true) {
  return useQuery({
    queryKey: ["catalog", "models-unified"],
    enabled,
    queryFn: async (): Promise<ModelsCatalogResponse> => {
      const { data, error, response } = await browserApi.GET("/v1/models/catalog");
      if (error || !response.ok || !data) throwOnApiError(error, response);
      return data as ModelsCatalogResponse;
    },
    staleTime: CATALOG_STALE_MS,
  });
}

/** @deprecated Prefer useUnifiedModelsCatalog */
export function useOcrModelsCatalog() {
  return useQuery({
    queryKey: ["catalog", "ocr-models"],
    queryFn: async () => {
      const unified = await browserApi.GET("/v1/models/catalog");
      if (unified.data && unified.response.ok) {
        const body = unified.data as ModelsCatalogResponse;
        return {
          models: body.models
            .filter((m) => m.kind === "document_model")
            .map((m) => ({
              id: m.id,
              label: m.label,
              engine: m.engine ?? "",
              runtime: m.runtime,
              description: m.description ?? "",
              available: m.available,
              availabilityNote: m.availabilityNote,
              isDefault: m.isDefault,
            })),
          defaultModel: body.defaultDocumentModel,
        };
      }
      const { data, error, response } = await browserApi.GET("/v1/ocr/models");
      if (error || !response.ok || !data) throwOnApiError(error, response);
      return data as import("@/lib/api/ocr").OcrModelsResponse;
    },
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
    queryFn: async (): Promise<PlatformConfig> => {
      const { data, error, response } = await browserApi.GET("/v1/platform/config");
      if (error || !response.ok || !data) throwOnApiError(error, response);
      return data as PlatformConfig;
    },
    staleTime: CATALOG_STALE_MS,
  });
}

export function useModelCatalog(enabled = true) {
  return useQuery({
    queryKey: ["catalog", "inference-models"],
    enabled,
    queryFn: async () => {
      const unified = await browserApi.GET("/v1/models/catalog");
      if (unified.data && unified.response.ok) {
        const body = unified.data as ModelsCatalogResponse;
        return {
          models: body.models.map((m) => ({
            id: m.id,
            label: m.label,
            kind: m.kind === "validation" ? "validation" : "document_model",
            runtime: m.runtime,
            isDefault: m.isDefault,
          })),
          defaultDocumentModel: body.defaultDocumentModel,
          defaultValidationModel: body.defaultValidationModel,
          inferenceMode: body.inferenceMode,
        };
      }
      const { data, error, response } = await browserApi.GET("/v1/inference/models");
      if (error || !response.ok || !data) throwOnApiError(error, response);
      return data as import("@/lib/api/inference").InferenceModelsResponse;
    },
    staleTime: CATALOG_STALE_MS,
  });
}
