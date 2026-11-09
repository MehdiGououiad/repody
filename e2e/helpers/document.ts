import path from "node:path";

/** The file the upload tests send: E2E_SAMPLE_DOCUMENT, or the committed invoice. */
export const SAMPLE_DOCUMENT =
  process.env.E2E_SAMPLE_DOCUMENT ??
  path.join(process.cwd(), "e2e", "fixtures", "documents", "Facture.pdf");
