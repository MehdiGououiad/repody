import type { Schema } from "@/lib/api/schema-types";

export type Audit = Schema["AuditListItem"];
export type AuditStatus = Audit["status"];
export type Kpi = Schema["Kpi"];
export type PerformancePoint = Schema["DayRuns"];
export type SeverityShare = Schema["SeverityShare"];
