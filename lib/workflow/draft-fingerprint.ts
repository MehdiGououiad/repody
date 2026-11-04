import type { DocumentDef, WorkflowRule } from "@/lib/types";

/** JSON with object keys sorted, so equal drafts compare equal whatever their key order. */
function stableJson(value: unknown): string {
  return JSON.stringify(value, (_key, v) =>
    v && typeof v === "object" && !Array.isArray(v)
      ? Object.fromEntries(Object.entries(v).sort(([a], [b]) => a.localeCompare(b)))
      : v
  );
}

/** Fingerprint for comparing the saved workflow with the draft being edited. */
export function workflowDraftFingerprint(input: {
  name: string;
  documents: DocumentDef[];
  rules: WorkflowRule[];
}): string {
  return stableJson({ name: input.name.trim(), documents: input.documents, rules: input.rules });
}

/** Fingerprint for rule-check requests (the name does not matter). */
export function rulesValidationFingerprint(
  documents: DocumentDef[],
  rules: WorkflowRule[]
): string {
  return stableJson({ documents, rules });
}
