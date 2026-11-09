/** Domain types: aliases of the API schema generated from the backend's OpenAPI document. */
import type { components } from "@/lib/api/generated/schema";

export type Schema = components["schemas"];

// Workflows, documents and rules
export type Workflow = Schema["WorkflowOut"];
/** draft, or active once deployed. Owned by the server: see docs/LIFECYCLES.md. */
export type WorkflowStatus = Workflow["status"];
export type DocumentDef = Schema["DocumentDef-Output"];
export type SchemaField = Schema["SchemaField-Output"];
export type WorkflowRule = Schema["Rule-Output"];
export type RuleScope = WorkflowRule["scope"];
export type RuleSeverity = WorkflowRule["severity"];
export type RuleCondition = Schema["Condition-Output"];
export type ConditionOperand = Schema["Operand-Output"];
export type TableAggregateLeft = Schema["TableAggregate-Output"];
export type ComparisonOp = RuleCondition["operator"];
export type ArithmeticOp = NonNullable<RuleCondition["arithmeticOp"]>;

// Runs and audit reports
export type RunProgress = Schema["RunProgress"];
export type RunAuditDetail = Schema["AuditDetail"];
export type RunAuditDocument = Schema["AuditDocument"];
export type RunAuditField = Schema["AuditField"];
export type RunAuditRule = Schema["AuditRule"];
/** passed | failed | skipped (a value the rule needs was not extracted). */
export type RuleStatus = RunAuditRule["status"];
export type RunAuditMetadata = Schema["RunTimings"];
export type RunDocumentExtractionMeta = Schema["ExtractionMeta"];
export type Audit = Schema["AuditListItem"];
export type AuditStatus = Audit["status"];
export type AuditListResponse = Schema["AuditList"];

// Dashboard and platform
export type Kpi = Schema["Kpi"];
export type PerformancePoint = Schema["DayRuns"];
export type SeverityShare = Schema["SeverityShare"];
export type QueueSnapshot = Schema["QueueCounts"];
export type PlatformConfig = Schema["PlatformConfig"];
/** The dashboard, and whether the API answered (a down API renders an empty dashboard). */
export type DashboardBundle = Schema["Dashboard"] & { apiLive: boolean };
