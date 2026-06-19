import type { DocumentDef } from "@/lib/types";

export function normalizeSchemaFieldName(name: string): string {
  return name.trim().toLowerCase().replace(/\s+/g, "_");
}

export function findDuplicateSchemaFieldNames(
  fields: Array<{ name: string }>
): string[] {
  const seen = new Map<string, string>();
  const duplicates: string[] = [];
  for (const field of fields) {
    const raw = field.name.trim();
    const norm = normalizeSchemaFieldName(raw);
    if (!norm) continue;
    if (seen.has(norm)) {
      const label = raw || seen.get(norm)!;
      if (!duplicates.includes(label)) duplicates.push(label);
    } else {
      seen.set(norm, raw);
    }
  }
  return duplicates;
}

export function validateDocumentSchemas(documents: DocumentDef[]): string[] {
  const errors: string[] = [];
  for (const doc of documents) {
    const dupes = findDuplicateSchemaFieldNames(doc.schema);
    if (dupes.length === 0) continue;
    const docLabel = doc.documentType.trim() || "Document";
    const joined = dupes.map((name) => `"${name}"`).join(", ");
    errors.push(
      `${docLabel}: duplicate field name(s) ${joined}. Each field name must be unique (case-insensitive).`
    );
  }
  return errors;
}
