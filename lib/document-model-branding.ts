/** Public document-model branding — keep in sync with document_model_branding.py */

export const REPODY_VLM_CATALOG_ID = "repody:vlm";
export const REPODY_VLM_LABEL = "Repody VLM";
export const SURYA_OCR2_CATALOG_ID = "surya:ocr2";
export const SURYA_OCR2_LABEL = "Surya OCR 2";

function isLegacyCatalogId(modelId: string | null | undefined): boolean {
  if (!modelId) return false;
  return modelId.trim() !== REPODY_VLM_CATALOG_ID;
}

export function publicDocumentModelLabel(modelId: string | null | undefined): string {
  if (!modelId) return REPODY_VLM_LABEL;
  const trimmed = modelId.trim();
  if (trimmed === SURYA_OCR2_CATALOG_ID) return SURYA_OCR2_LABEL;
  if (isLegacyCatalogId(trimmed) || trimmed === REPODY_VLM_CATALOG_ID) {
    return REPODY_VLM_LABEL;
  }
  return trimmed;
}
