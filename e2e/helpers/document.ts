import fs from "fs";
import path from "path";

const FIXTURE_DIR = path.join(process.cwd(), "e2e", "fixtures", "documents");

const CANDIDATES = [
  process.env.E2E_SAMPLE_DOCUMENT,
  path.join(FIXTURE_DIR, "sample-invoice.pdf"),
  path.join(FIXTURE_DIR, "sample-invoice.png"),
  path.join(FIXTURE_DIR, "sample-invoice.jpg"),
].filter(Boolean) as string[];

export function resolveSampleDocument(): string | null {
  for (const candidate of CANDIDATES) {
    if (fs.existsSync(candidate)) return candidate;
  }
  const dir = fs.readdirSync(FIXTURE_DIR, { withFileTypes: true });
  for (const entry of dir) {
    if (!entry.isFile()) continue;
    if (/\.(pdf|png|jpe?g)$/i.test(entry.name)) {
      return path.join(FIXTURE_DIR, entry.name);
    }
  }
  return null;
}

export function hasSampleDocument(): boolean {
  return resolveSampleDocument() !== null;
}
