/** New, empty workflow items for the builder (every field the API returns is set). */
import { DEFAULT_NUEXTRACT_TEMPLATE_TYPE } from "@/lib/nuextract-types";
import type { DocumentDef, RuleCondition, SchemaField, Workflow, WorkflowRule } from "@/lib/types";
import { shortId } from "@/lib/utils";

export function newSchemaField(partial: Partial<SchemaField> = {}): SchemaField {
  return {
    id: `f${shortId()}`,
    name: "",
    description: "",
    templateType: DEFAULT_NUEXTRACT_TEMPLATE_TYPE,
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
  return {
    id: shortId(),
    left: { kind: "field", value: "" },
    operator: "==",
    right: { kind: "literal", value: "" },
    arithmeticOp: null,
    leftExtra: null,
    tableAggregate: null,
  };
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
