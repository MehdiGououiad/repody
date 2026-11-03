/** Public document-model branding - keep in sync with extraction/branding.py */

export const REPODY_VLM_LABEL = "Repody VLM";

/** Every stored model id (including retired engines) is the one NuExtract model. */
export function publicDocumentModelLabel(_modelId: string | null | undefined): string {
  return REPODY_VLM_LABEL;
}
