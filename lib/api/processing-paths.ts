export type ReadPathOption = {
  id: string;
  label: string;
  description: string;
  readKind: string;
  showOcrModel?: boolean;
  ocrEngine?: string | null;
};

export type ValidationModeOption = {
  id: string;
  label: string;
  description: string;
};

export type ProcessingPathsResponse = {
  paths: ReadPathOption[];
  validationModes: ValidationModeOption[];
  defaultPath: string;
  defaultValidationMode: string;
};

/** Map legacy workflow values to supported read paths. */
export function normalizeReadPath(mode: string | undefined): string {
  const raw = (mode ?? "document_model").toLowerCase();
  if (raw === "document_model" || raw === "vlm") return "document_model";
  if (raw === "paddle_ocr" || raw === "paddle" || raw === "ocr" || raw === "pp-ocrv6") {
    return "document_model";
  }
  return "document_model";
}

export function normalizeValidationMode(validationMode: string | undefined): "logic_only" {
  const raw = (validationMode ?? "").toLowerCase();
  if (raw === "logic_only") return "logic_only";
  return "logic_only";
}
