import type { components } from "@/lib/api/generated/schema";

export type Schema = components["schemas"];

export type ModelsCatalogResponse = Schema["ModelsCatalogResponse"];
export type CatalogModelEntry = Schema["CatalogModelEntry"];
export type PlatformConfigResponse = Schema["PlatformConfigResponse"];
export type RunPollResponse = Schema["RunPollResponse"];
export type RunCreatedResponse = Schema["RunCreatedResponse"];
export type HealthLiveResponse = Schema["HealthLiveResponse"];
export type HealthReadinessResponse = Schema["HealthReadinessResponse"];
export type CreateRunJsonBody = Schema["CreateRunJsonBody"];
