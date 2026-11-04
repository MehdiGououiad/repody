import type { DocumentDef, SchemaField, WorkflowRule } from "@/lib/types";

function normalizeSchemaField(field: SchemaField): SchemaField {
  return {
    id: field.id,
    name: field.name ?? "",
    description: field.description ?? "",
    ...(field.templateType ? { templateType: field.templateType } : {}),
    ...(field.enumValues?.length ? { enumValues: [...field.enumValues] } : {}),
    ...(field.children?.length
      ? {
          children: field.children
            .map(normalizeSchemaField)
            .sort((a, b) => a.id.localeCompare(b.id)),
        }
      : {}),
    ...(field.sampleValue !== undefined && field.sampleValue !== ""
      ? { sampleValue: field.sampleValue }
      : {}),
  };
}

function normalizeDocument(doc: DocumentDef): DocumentDef {
  return {
    id: doc.id,
    documentType: doc.documentType ?? "",
    schema: [...doc.schema].map(normalizeSchemaField).sort((a, b) => a.id.localeCompare(b.id)),
    extractionInstructions: doc.extractionInstructions ?? "",
    markdownExtraction: doc.markdownExtraction ?? false,
    extractionIclExamples: [...(doc.extractionIclExamples ?? [])],
  };
}

function normalizeRule(rule: WorkflowRule): WorkflowRule {
  return {
    id: rule.id,
    name: rule.name ?? "",
    kind: rule.kind,
    scope: rule.scope,
    appliesTo: [...rule.appliesTo].sort(),
    body: rule.body ?? "",
    severity: rule.severity,
    ...(rule.conditions?.length
      ? {
          conditions: rule.conditions,
          conditionJunction: rule.conditionJunction ?? "AND",
        }
      : {}),
  };
}

/** Stable fingerprint for comparing saved vs in-progress workflow drafts. */
export function workflowDraftFingerprint(input: {
  name: string;
  documents: DocumentDef[];
  rules: WorkflowRule[];
}): string {
  const documents = [...input.documents]
    .map(normalizeDocument)
    .sort((a, b) => a.id.localeCompare(b.id));
  const rules = [...input.rules].map(normalizeRule).sort((a, b) => a.id.localeCompare(b.id));

  return JSON.stringify({
    name: input.name.trim(),
    documents,
    rules,
  });
}

/** Fingerprint for rule validation requests (name excluded). */
export function rulesValidationFingerprint(
  documents: DocumentDef[],
  rules: WorkflowRule[]
): string {
  return workflowDraftFingerprint({ name: "", documents, rules });
}
