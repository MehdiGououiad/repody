/** New, empty workflow items for the builder (every field the API returns is set). */
import { fieldRef, literal } from "@/lib/rules/conditions";
import type { DocumentDef, RuleCondition, SchemaField, Workflow, WorkflowRule } from "@/lib/types";
import { shortId } from "@/lib/utils";

export const DEFAULT_TEMPLATE_TYPE = "verbatim-string";

export function newSchemaField(partial: Partial<SchemaField> = {}): SchemaField {
  return {
    id: `f${shortId()}`,
    name: "",
    description: "",
    templateType: DEFAULT_TEMPLATE_TYPE,
    enumValues: [],
    children: [],
    ...partial,
  };
}

export function newDocument(): DocumentDef {
  return {
    id: `doc${shortId()}`,
    documentType: "",
    schema: [],
    extractionInstructions: "",
    markdownExtraction: false,
    extractionIclExamples: [],
  };
}

export function newCondition(): RuleCondition {
  return { id: shortId(), left: fieldRef(), operator: "==", right: literal() };
}

export function newRule(documents: DocumentDef[]): WorkflowRule {
  return {
    id: `r${shortId()}`,
    name: "",
    scope: "intra",
    appliesTo: documents[0] ? [documents[0].id] : [],
    severity: "flag",
    conditions: [newCondition()],
  };
}

export function newWorkflow(): Workflow {
  return {
    id: `wf-${shortId()}`,
    name: "",
    description: "",
    status: "draft",
    owner: "",
    documents: [newDocument()],
    rules: [],
    deployedAt: null,
    apiKey: null,
    apiKeyHint: null,
    totalRuns: 0,
    successRate: 0,
    lastRun: null,
    apiStats: null,
  };
}
