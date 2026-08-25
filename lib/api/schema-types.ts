import type { components } from "@/lib/api/generated/schema";

export type Schema = components["schemas"];

export type ModelsCatalogResponse = Schema["ModelsCatalogResponse"];
export type CatalogModelEntry = Schema["CatalogModelEntry"];
export type PlatformConfigResponse = Schema["PlatformConfigResponse"];
export type AuditListResponse = Schema["AuditListResponse"];
export type DashboardResponse = Schema["DashboardResponse"];
export type QueueSnapshot = Schema["QueueSnapshot"];
