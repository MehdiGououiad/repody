/** Public document-model branding — keep in sync with extraction/branding.py */

export const REPODY_VLM_CATALOG_ID = "repody:vlm";
export const REPODY_VLM_LABEL = "Repody VLM";
export const REPODY_VLM_CLOUD_CATALOG_ID = "repody:vlm:cloud";
export const REPODY_VLM_CLOUD_LABEL = "NuExtract Cloud";
export const PADDLEOCR_V6_CATALOG_ID = "paddleocr:v6";
export const PADDLEOCR_V6_LABEL = "PP-OCRv6";
export const PADDLEOCR_QWEN_CATALOG_ID = "paddleocr:qwen";
export const PADDLEOCR_QWEN_LABEL = "PP-OCRv6 + Qwen";
export const GLM_OCR_CATALOG_ID = "glm:ocr";
export const GLM_OCR_LABEL = "GLM-OCR";
export const GLM_OCR_QWEN_CATALOG_ID = "glm:qwen";
export const GLM_OCR_QWEN_LABEL = "GLM-OCR + Qwen";

const MARKDOWN_ONLY_IDS = new Set([
  PADDLEOCR_V6_CATALOG_ID,
  GLM_OCR_CATALOG_ID,
]);

export function publicDocumentModelLabel(modelId: string | null | undefined): string {
  if (!modelId) return REPODY_VLM_LABEL;
  const trimmed = modelId.trim();
  if (trimmed === REPODY_VLM_CATALOG_ID) {
    return REPODY_VLM_LABEL;
  }
  if (trimmed === REPODY_VLM_CLOUD_CATALOG_ID) {
    return REPODY_VLM_CLOUD_LABEL;
  }
  if (trimmed === PADDLEOCR_V6_CATALOG_ID) {
    return PADDLEOCR_V6_LABEL;
  }
  if (trimmed === PADDLEOCR_QWEN_CATALOG_ID) {
    return PADDLEOCR_QWEN_LABEL;
  }
  if (trimmed === GLM_OCR_CATALOG_ID) {
    return GLM_OCR_LABEL;
  }
  if (trimmed === GLM_OCR_QWEN_CATALOG_ID) {
    return GLM_OCR_QWEN_LABEL;
  }
  return trimmed;
}

export function isMarkdownOnlyCatalogId(modelId: string | null | undefined): boolean {
  return MARKDOWN_ONLY_IDS.has((modelId || "").trim());
}
