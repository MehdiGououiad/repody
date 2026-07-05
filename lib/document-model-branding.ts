/** Public document-model branding — keep in sync with document_model_branding.py */

export const REPODY_VLM_CATALOG_ID = "repody:vlm";
export const REPODY_VLM_LABEL = "Repody VLM";

export function publicDocumentModelLabel(modelId: string | null | undefined): string {
  if (!modelId) return REPODY_VLM_LABEL;
  const trimmed = modelId.trim();
  if (trimmed === REPODY_VLM_CATALOG_ID) {
    return REPODY_VLM_LABEL;
  }
  return trimmed;
}
