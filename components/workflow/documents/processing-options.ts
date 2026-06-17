import type { CatalogModelEntry } from "@/lib/api/schema-types";
import { REPODY_VLM_CATALOG_ID } from "@/lib/document-model-branding";
import type {
  ReadPathOption,
  ValidationModeOption,
} from "@/lib/api/processing-paths";
import type { ValidationModeId } from "@/lib/types";

export type ProcessingOptions = {
  paths: ReadPathOption[];
  validationModes: ValidationModeOption[];
  ocrModels: CatalogModelEntry[];
  defaultPath: string;
  defaultValidation: ValidationModeId;
  defaultOcr: string;
  loaded: boolean;
  error: boolean;
};

export const EMPTY_PROCESSING_OPTIONS: ProcessingOptions = {
  paths: [],
  validationModes: [],
  ocrModels: [],
  defaultPath: "document_model",
  defaultValidation: "logic_only",
  defaultOcr: REPODY_VLM_CATALOG_ID,
  loaded: false,
  error: false,
};
