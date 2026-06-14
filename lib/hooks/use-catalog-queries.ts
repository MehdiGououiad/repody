"use client";

import { useQuery } from "@tanstack/react-query";
import { browserApi, throwOnApiError } from "@/lib/api/openapi-client";
import type { PlatformConfig } from "@/lib/api/platform-config";
import type { InferenceModelsResponse } from "@/lib/api/inference";
import type { OcrModelsResponse } from "@/lib/api/ocr";
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

export function useOcrModelsCatalog() {
  return useQuery({
    queryKey: ["catalog", "ocr-models"],
    queryFn: async (): Promise<OcrModelsResponse> => {
      const { data, error, response } = await browserApi.GET("/v1/ocr/models");
      if (error || !response.ok || !data) throwOnApiError(error, response);
      return data as OcrModelsResponse;
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
    queryFn: async (): Promise<InferenceModelsResponse> => {
      const { data, error, response } = await browserApi.GET("/v1/inference/models");
      if (error || !response.ok || !data) throwOnApiError(error, response);
      return data as InferenceModelsResponse;
    },
    staleTime: CATALOG_STALE_MS,
  });
}
