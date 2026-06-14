import { browserApi, throwOnApiError } from "@/lib/api/openapi-client";

export type ReadPathOption = {
  id: string;
  label: string;
  description: string;
  readKind: "document_model";
  showOcrModel?: boolean;
  ocrEngine?: "document_model" | null;
};

export type ValidationModeOption = {
  id: "logic_only";
  label: string;
  description: string;
};

export type ProcessingPathsResponse = {
  paths: ReadPathOption[];
  validationModes: ValidationModeOption[];
  defaultPath: string;
  defaultValidationMode: string;
};

export async function fetchProcessingPaths(): Promise<ProcessingPathsResponse> {
  const { data, error, response } = await browserApi.GET("/v1/processing-paths");
  if (error || !response.ok || !data) throwOnApiError(error, response);
  return data as ProcessingPathsResponse;
}

/** Map legacy workflow values to the current document-model read path. */
export function normalizeReadPath(mode: string | undefined): string {
  const raw = (mode ?? "document_model").toLowerCase();
  if (raw === "document_model" || raw === "vlm") return "document_model";
  return "document_model";
}

export function normalizeValidationMode(
  validationMode: string | undefined,
  _extractionMode?: string | undefined
): "logic_only" {
  const raw = (validationMode ?? "").toLowerCase();
  if (raw === "logic_only") return "logic_only";
  return "logic_only";
}
