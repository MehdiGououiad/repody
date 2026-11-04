import type { components } from "@/lib/api/generated/schema";

export type Schema = components["schemas"];

export type AuditListResponse = Schema["AuditList"];
export type DashboardResponse = Schema["Dashboard"];
export type QueueSnapshot = Schema["QueueCounts"];
export type PlatformConfig = Schema["PlatformConfig"];
export type RunProgress = Schema["RunProgress"];
