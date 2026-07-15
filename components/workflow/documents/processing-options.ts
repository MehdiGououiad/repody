import type { CatalogModelEntry } from "@/lib/api/schema-types";

export type ProcessingOptions = {
  documentModelIds: CatalogModelEntry[];
  defaultDocumentModel: string;
  loaded: boolean;
  error: boolean;
};

export const EMPTY_PROCESSING_OPTIONS: ProcessingOptions = {
  documentModelIds: [],
  defaultDocumentModel: "",
  loaded: false,
  error: false,
};
