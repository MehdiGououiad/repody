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
