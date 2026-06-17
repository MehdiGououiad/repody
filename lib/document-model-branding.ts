/** Public document-model branding — keep in sync with document_model_branding.py */

export const REPODY_VLM_CATALOG_ID = "repody:vlm";
export const REPODY_VLM_LABEL = "Repody VLM";

function isLegacyCatalogId(modelId: string | null | undefined): boolean {
  return !modelId || modelId.trim() !== REPODY_VLM_CATALOG_ID;
}

export function publicDocumentModelLabel(modelId: string | null | undefined): string {
  if (isLegacyCatalogId(modelId) || modelId === REPODY_VLM_CATALOG_ID) {
    return REPODY_VLM_LABEL;
  }
  return modelId ?? REPODY_VLM_LABEL;
}
