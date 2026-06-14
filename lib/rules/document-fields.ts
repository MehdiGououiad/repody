import type { DocumentDef } from "@/lib/types";
import { fieldToken } from "@/lib/rules/expression";

export type DocumentFieldOption = { label: string; token: string };

export function resolveDocumentFields(
  documents: DocumentDef[],
  appliesTo: string[]
): DocumentFieldOption[] {
  const targets = appliesTo.length
    ? documents.filter((doc) => appliesTo.includes(doc.id))
    : documents;
  const multi = targets.length > 1;

  const fields: DocumentFieldOption[] = [];
  for (const doc of targets) {
    for (const field of doc.schema) {
      if (!field.name.trim()) continue;
      const token = multi
        ? `${fieldToken(doc.documentType)}.${fieldToken(field.name)}`
        : fieldToken(field.name);
      fields.push({
        label: multi ? `${doc.documentType}.${field.name}` : field.name,
        token,
      });
    }
  }
  return fields;
}
