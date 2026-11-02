import type { Schema } from "@/lib/api/schema-types";

export type Audit = Schema["AuditListItem"];
export type KpiMetric = Schema["KpiMetric"];
export type PerformancePoint = Schema["PerformancePoint"];
export type ViolationBreakdown = Schema["ViolationBreakdown"];
export type HealthAlert = Schema["HealthAlert"];
export type AuditStatus = Audit["status"];
