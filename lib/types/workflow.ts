/** Workflow builder and rule authoring types — aligned with backend workflow schemas. */

export type RuleKind = "logic" | "llm";
export type RuleSeverity = "reject" | "flag" | "info";
export type RuleEvalStatus = "passed" | "failed" | "skipped" | "error" | "warning";
export type RuleScope = "intra" | "cross";

export interface SchemaField {
  id: string;
  name: string;
  description: string;
  /** NuExtract template leaf type, e.g. verbatim-string, number, date-time. */
  templateType?: string;
  /** Optional value for dry-run rule validation without uploading a file. */
  sampleValue?: string;
}

export type ReadPathId = "document_model";
export type ProcessingPathId = ReadPathId;
export type ValidationModeId = "logic_only";

export interface DocumentDef {
  id: string;
  documentType: string;
  schema: SchemaField[];
  extractionMode?: ProcessingPathId | string;
  validationMode?: ValidationModeId | string;
  documentModelId?: string | null;
  extractionInstructions?: string;
  markdownExtraction?: boolean;
}

export type ArithmeticOp = "+" | "-" | "*" | "/";

export type ComparisonOp =
  | "==" | "!=" | ">" | ">=" | "<" | "<="
  | "IN" | "NOT_IN"
  | "EXISTS" | "IS_EMPTY";

export type ConditionJunction = "AND" | "OR";

export interface ConditionOperand {
  kind: "field" | "literal";
  value: string;
}

export interface RuleCondition {
  id: string;
  left: ConditionOperand;
  arithmeticOp?: ArithmeticOp;
  leftExtra?: ConditionOperand;
  operator: ComparisonOp;
  right?: ConditionOperand;
}

export interface WorkflowRule {
  id: string;
  name: string;
  kind: RuleKind;
  scope: RuleScope;
  appliesTo: string[];
  conditions?: RuleCondition[];
  conditionJunction?: ConditionJunction;
  body: string;
  severity: RuleSeverity;
}

export interface Workflow {
  id: string;
  name: string;
  description: string;
  status: "active" | "draft" | "paused";
  owner: string;
  lastRun: string | null;
  successRate: number;
  totalRuns: number;
  documents: DocumentDef[];
  rules: WorkflowRule[];
  deployedAt?: string;
  apiKey?: string;
  apiKeyHint?: string;
  apiStats?: WorkflowApiStats;
}

export interface RuleTemplate {
  id: string;
  name: string;
  kind: RuleKind;
  scope: RuleScope;
  description: string;
  body: string;
  severity: RuleSeverity;
}

export interface WorkflowApiStats {
  apiCallsToday: number;
  apiCallsTotal: number;
  avgLatencyMs: number;
  callSeries: { day: string; calls: number }[];
  topFailingRules: { name: string; count: number; severity: RuleSeverity }[];
}
