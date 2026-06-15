export type CatalogModelEntry = {
  id: string;
  label: string;
  kind: string;
  engine?: string;
  runtime: string;
  description?: string;
  available: boolean;
  availabilityNote?: string | null;
  isDefault?: boolean;
};

export type ModelsCatalogResponse = {
  models: CatalogModelEntry[];
  defaultDocumentModel: string;
  defaultValidationModel?: string | null;
  inferenceMode: string;
};
