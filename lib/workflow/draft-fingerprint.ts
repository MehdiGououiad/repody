import { syncRuleBodies } from "@/lib/rules/sync-rules";
import type { DocumentDef, SchemaField, WorkflowRule } from "@/lib/types";

function normalizeSchemaField(field: SchemaField): SchemaField {
  return {
    id: field.id,
    name: field.name ?? "",
    description: field.description ?? "",
    ...(field.templateType ? { templateType: field.templateType } : {}),
    ...(field.enumValues?.length ? { enumValues: [...field.enumValues] } : {}),
    ...(field.children?.length
      ? { children: field.children.map(normalizeSchemaField).sort((a, b) => a.id.localeCompare(b.id)) }
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
    schema: [...doc.schema]
      .map(normalizeSchemaField)
      .sort((a, b) => a.id.localeCompare(b.id)),
    extractionMode: doc.extractionMode ?? "document_model",
    validationMode: doc.validationMode ?? "logic_only",
    documentModelId: doc.documentModelId ?? null,
    extractionInstructions: doc.extractionInstructions ?? "",
    markdownExtraction: doc.markdownExtraction ?? false,
    extractionIclExamples: [...(doc.extractionIclExamples ?? [])],
  };
}

function normalizeRule(rule: WorkflowRule): WorkflowRule {
  const synced = syncRuleBodies([rule])[0];
  return {
    id: synced.id,
    name: synced.name ?? "",
    kind: synced.kind,
    scope: synced.scope,
    appliesTo: [...synced.appliesTo].sort(),
    body: synced.body ?? "",
    severity: synced.severity,
    ...(synced.conditions?.length
      ? {
          conditions: synced.conditions,
          conditionJunction: synced.conditionJunction ?? "AND",
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
  const rules = syncRuleBodies(input.rules)
    .map(normalizeRule)
    .sort((a, b) => a.id.localeCompare(b.id));

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
