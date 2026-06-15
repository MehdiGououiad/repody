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
