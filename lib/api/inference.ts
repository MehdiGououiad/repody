import { browserApi } from "@/lib/api/openapi-client";

export type InferenceModel = {
  id: string;
  label: string;
  kind: string;
  runtime: string;
  isDefault?: boolean;
};

export type InferenceModelsResponse = {
  models: InferenceModel[];
  defaultDocumentModel: string;
  defaultValidationModel?: string | null;
  inferenceMode: string;
};

export async function fetchInferenceModels(): Promise<InferenceModelsResponse> {
  const { data, error, response } = await browserApi.GET("/v1/inference/models");
  if (error || !response.ok || !data) {
    throw new Error(`HTTP ${response.status}`);
  }
  return data as InferenceModelsResponse;
}
