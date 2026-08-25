// Convenience barrel for the domain types consumed across the app. Audit and
// run-report types are imported straight from `@/lib/types/audit`, so they are
// deliberately absent here.
export type {
  Audit,
  AuditStatus,
  HealthAlert,
  KpiMetric,
  PerformancePoint,
  ViolationBreakdown,
} from "@/lib/types/dashboard";
export type {
  ArithmeticOp,
  ComparisonOp,
  ConditionJunction,
  ConditionOperand,
  DocumentDef,
  RuleCondition,
  RuleKind,
  RuleScope,
  RuleSeverity,
  RuleTemplate,
  SchemaField,
  TableAggregateLeft,
  Workflow,
  WorkflowRule,
} from "@/lib/types/workflow";
