export type AuditStatus = "passed" | "failed" | "warning" | "running";

export interface Audit {
  id: string;
  status: AuditStatus;
  workflowId: string;
  workflowName: string;
  entity: string;
  timestamp: string;
  rows: number | null;
  failedRules?: number;
}

export interface AuditDetail extends Audit {
  documentUrl: string;
  extractedFields: ExtractedField[];
  rules: RuleEvaluation[];
}

export interface ExtractedField {
  key: string;
  value: string;
  type: "string" | "currency" | "number" | "date" | "percent" | "calculated";
  bbox?: { x: number; y: number; w: number; h: number };
  failedRuleIds?: string[];
}

export type RuleKind = "logic" | "llm";
export type RuleSeverity = "reject" | "flag" | "info";

export type RuleEvalStatus = "passed" | "failed" | "skipped" | "error" | "warning";

export interface RuleEvaluation {
  id: string;
  name: string;
  kind: RuleKind;
  status: RuleEvalStatus;
  description: string;
  detail?: string;
  expectedValue?: string;
  actualValue?: string;
  affectedFieldKeys?: string[];
  severity: RuleSeverity;
}

/**
 * A "what to extract" entry — pure intent.
 * The platform decides type / extraction method automatically.
 */
export interface SchemaField {
  id: string;
  name: string;
  description: string;
  /** Optional value for dry-run rule validation without uploading a file. */
  sampleValue?: string;
}

/**
 * One document type processed by this workflow (platform + type + fields to extract).
 * A workflow can process multiple document types for cross-document validation.
 */
/** Document extraction uses a registered document model (Docker Model Runner). */
export type ReadPathId = "document_model";

export type ProcessingPathId = ReadPathId;

export type ValidationModeId = "logic_only";

export interface DocumentDef {
  id: string;
  documentType: string;
  schema: SchemaField[];
  /** Read path: document_model */
  extractionMode?: ProcessingPathId | string;
  /** Validation: logic_only */
  validationMode?: ValidationModeId | string;
  /** Registered document model id (e.g. repody:vlm). */
  ocrModel?: string | null;
}

// ── Structured condition types (for logic rules) ─────────────────────────────

export type ArithmeticOp = "+" | "-" | "*" | "/";

/** == != > >= < <= IN NOT_IN EXISTS IS_EMPTY */
export type ComparisonOp =
  | "==" | "!=" | ">" | ">=" | "<" | "<="
  | "IN" | "NOT_IN"
  | "EXISTS" | "IS_EMPTY";

export type ConditionJunction = "AND" | "OR";

/** One side of a comparison — either a field token or a literal string/number. */
export interface ConditionOperand {
  kind: "field" | "literal";
  value: string;
}

/**
 * A single comparison condition.
 * Left side can optionally include arithmetic: left.value arithmeticOp leftExtra.value
 * e.g. subtotal + tax == total_amount → left=subtotal, arithmeticOp=+, leftExtra=tax, op===, right=total_amount(field)
 */
export interface RuleCondition {
  id: string;
  left: ConditionOperand;
  arithmeticOp?: ArithmeticOp;
  leftExtra?: ConditionOperand;
  operator: ComparisonOp;
  right?: ConditionOperand; // absent when operator is EXISTS / IS_EMPTY
}

// ── Workflow rule ─────────────────────────────────────────────────────────────

export interface WorkflowRule {
  id: string;
  name: string;
  kind: RuleKind;
  /** Explicit user choice: one document or across two documents. */
  scope: RuleScope;
  /**
   * IDs of the DocumentDef(s) this rule applies to.
   * scope=intra → 1 ID; scope=cross → 2 IDs.
   */
  appliesTo: string[];
  /**
   * For logic rules: structured conditions (source of truth).
   * For LLM rules: the natural-language prompt (body only).
   */
  conditions?: RuleCondition[];
  conditionJunction?: ConditionJunction;
  /** Auto-generated from conditions for logic rules; the prompt for LLM rules. */
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
  /** One or more document types this workflow ingests. */
  documents: DocumentDef[];
  rules: WorkflowRule[];
  /** Set when the workflow has been deployed. */
  deployedAt?: string;
  /** Legacy field retained for stored workflow compatibility. */
  defaultLlmModel?: string | null;
  apiKey?: string;
  apiKeyHint?: string;
  apiStats?: WorkflowApiStats;
}

/** Library template — scope is for display only; appliesTo is resolved at add-time. */
export type RuleScope = "intra" | "cross";

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

export interface KpiMetric {
  id: string;
  label: string;
  value: string;
  rawValue: number;
  delta: number;
  deltaUnit: "percent" | "absolute";
  direction: "up" | "down";
  positive: boolean;
  series: { day: string; value: number }[];
  icon: string;
}

export interface PerformancePoint {
  day: string;
  runs: number;
  prevRuns: number;
}

export interface ViolationBreakdown {
  type: string;
  share: number;
  color: "danger" | "warning" | "info" | "neutral";
}

export interface HealthAlert {
  id: string;
  severity: "info" | "warning" | "danger";
  titleKey: string;
  detailKey: string;
  href?: string;
}
