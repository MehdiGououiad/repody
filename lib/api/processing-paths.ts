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

export function normalizeReadPath(mode: string | undefined): string {
  const raw = (mode ?? "document_model").toLowerCase();
  if (raw === "document_model" || raw === "vlm") return "document_model";
  return "document_model";
}

export function normalizeValidationMode(
  validationMode: string | undefined,
): "logic_only" | "logic_and_llm" {
  const raw = (validationMode ?? "logic_only").toLowerCase();
  if (raw === "logic_and_llm") return "logic_and_llm";
  return "logic_only";
}
