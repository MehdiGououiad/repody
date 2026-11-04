/** Workflow, document and rule types: aliases of the generated API schema. */
import type { Schema } from "@/lib/api/schema-types";

export type SchemaField = Schema["SchemaField-Output"];
export type DocumentDef = Schema["DocumentDef-Output"];
export type ConditionOperand = Schema["Operand-Output"];
export type TableAggregateLeft = Schema["TableAggregate-Output"];
export type RuleCondition = Schema["Condition-Output"];
export type ComparisonOp = RuleCondition["operator"];
export type ArithmeticOp = NonNullable<RuleCondition["arithmeticOp"]>;
export type WorkflowRule = Schema["Rule-Output"];
export type RuleScope = WorkflowRule["scope"];
export type RuleSeverity = WorkflowRule["severity"];
export type Workflow = Schema["WorkflowOut"];
