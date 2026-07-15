import { DEFAULT_NUEXTRACT_TEMPLATE_TYPE } from "@/lib/nuextract-types";
import type { DocumentDef, SchemaField } from "@/lib/types";
import { fieldToken } from "@/lib/rules/expression";

export type DocumentFieldOption = {
  label: string;
  token: string;
  templateType: string;
  tableParent?: string;
};

export type TableFieldOption = {
  label: string;
  token: string;
  columns: Array<{ label: string; name: string }>;
};

function fieldOptionsForSchema(
  doc: DocumentDef,
  multi: boolean,
): DocumentFieldOption[] {
  const fields: DocumentFieldOption[] = [];
  for (const field of doc.schema) {
    if (!field.name.trim()) continue;
    const parentToken = multi
      ? `${fieldToken(doc.documentType)}.${fieldToken(field.name)}`
      : fieldToken(field.name);
    fields.push({
      label: multi ? `${doc.documentType}.${field.name}` : field.name,
      token: parentToken,
      templateType: field.templateType ?? DEFAULT_NUEXTRACT_TEMPLATE_TYPE,
    });
    if (field.templateType === "object-array") {
      for (const child of field.children ?? []) {
        if (!child.name.trim()) continue;
        fields.push({
          label: multi
            ? `${doc.documentType}.${field.name}.${child.name}`
            : `${field.name}.${child.name}`,
          token: `${parentToken}.${fieldToken(child.name)}`,
          templateType: child.templateType ?? DEFAULT_NUEXTRACT_TEMPLATE_TYPE,
          tableParent: parentToken,
        });
      }
    }
  }
  return fields;
}

export function resolveDocumentFields(
  documents: DocumentDef[],
  appliesTo: string[],
): DocumentFieldOption[] {
  const targets = appliesTo.length
    ? documents.filter((doc) => appliesTo.includes(doc.id))
    : documents;
  const multi = documents.length > 1;
  return targets.flatMap((doc) => fieldOptionsForSchema(doc, multi));
}

export function resolveTableFields(
  documents: DocumentDef[],
  appliesTo: string[],
): TableFieldOption[] {
  const targets = appliesTo.length
    ? documents.filter((doc) => appliesTo.includes(doc.id))
    : documents;
  const multi = documents.length > 1;
  const tables: TableFieldOption[] = [];

  for (const doc of targets) {
    for (const field of doc.schema) {
      if (!field.name.trim() || field.templateType !== "object-array") continue;
      const token = multi
        ? `${fieldToken(doc.documentType)}.${fieldToken(field.name)}`
        : fieldToken(field.name);
      tables.push({
        label: multi ? `${doc.documentType}.${field.name}` : field.name,
        token,
        columns: (field.children ?? [])
          .filter((child: SchemaField) => child.name.trim())
          .map((child: SchemaField) => ({
            label: child.name,
            name: fieldToken(child.name),
          })),
      });
    }
  }
  return tables;
}
