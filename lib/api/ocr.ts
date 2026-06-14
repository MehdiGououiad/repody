import { browserApi, throwOnApiError } from "@/lib/api/openapi-client";

export type OcrModelOption = {
  id: string;
  label: string;
  engine: "document_model";
  runtime: "docker_model_runner";
  description?: string;
  available?: boolean;
  availabilityNote?: string | null;
  isDefault?: boolean;
};

export type OcrModelsResponse = {
  models: OcrModelOption[];
  defaultModel: string;
};

export async function fetchOcrModels(): Promise<OcrModelsResponse> {
  const { data, error, response } = await browserApi.GET("/v1/ocr/models");
  if (error || !response.ok || !data) throwOnApiError(error, response);
  return data as OcrModelsResponse;
}
