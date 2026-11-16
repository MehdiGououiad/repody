/** Domain types: aliases of the API schema generated from the backend's OpenAPI document. */
import type { components } from "@/lib/api/generated/schema";

export type Schema = components["schemas"];

// Workflows, documents and rules
export type Workflow = Schema["WorkflowOut"];
/** draft, or active once deployed. Owned by the server: see docs/LIFECYCLES.md. */
export type DocumentDef = Schema["DocumentDef-Output"];
export type SchemaField = Schema["SchemaField-Output"];
export type WorkflowRule = Schema["Rule-Output"];
export type RuleScope = WorkflowRule["scope"];
export type RuleSeverity = WorkflowRule["severity"];
export type RuleCondition = Schema["Condition-Output"];
export type ComparisonOp = RuleCondition["operator"];
/** The left side of a condition: a field, arithmetic on two fields, or a table aggregate. */
export type ConditionExpression = RuleCondition["left"];
export type FieldRef = Schema["FieldRef-Output"];
export type LiteralValue = Schema["LiteralValue-Output"];
export type Arithmetic = Schema["Arithmetic-Output"];
export type Aggregate = Schema["Aggregate-Output"];
export type ConditionOperand = FieldRef | LiteralValue;
export type ArithmeticOp = Arithmetic["op"];
export type AggregateFn = Aggregate["fn"];
export type RuleCheck = Schema["RuleCheck"];
export type Catalog = Schema["Catalog"];
export type TemplateTypeGroup = Schema["TemplateTypeInfo"]["group"];

// Runs and audit reports
export type RunProgress = Schema["RunProgress"];
export type RunAuditDetail = Schema["AuditDetail"];
export type RunAuditDocument = Schema["AuditDocument"];
export type RunAuditRule = Schema["AuditRule"];
/** passed | failed | skipped (a value the rule needs was not extracted). */
export type RunDocumentExtractionMeta = Schema["ExtractionMeta"];
export type Audit = Schema["AuditListItem"];

// Dashboard and platform
export type Dashboard = Schema["Dashboard"];
export type Kpi = Schema["Kpi"];
export type PlatformConfig = Schema["PlatformConfig"];
export type Access = Schema["Access"];
export type Permission = Access["permissions"][number];

// Admin area (platform admins)
export type AdminOverview = Schema["AdminOverview"];
export type ClientSummary = Schema["ClientSummary"];
export type ClientDetail = Schema["ClientDetail"];
export type ClientUser = Schema["ClientUser"];
export type ClientRole = NonNullable<Schema["ClientUser"]["role"]>;
export type LedgerEntry = Schema["LedgerEntry"];
export type SharedWorkflow = Schema["SharedWorkflow"];
export type AdminEvent = Schema["AdminEventOut"];
export type TemporaryPassword = Schema["TemporaryPassword"];
export type AccessRequest = Schema["AccessRequestOut"];
