import { cache } from "react";
import type { Workflow } from "@/lib/types";
import type { RunAuditDetail } from "@/lib/types/audit";
import { serverApi, throwOnApiError } from "@/lib/api/openapi-client";

export async function fetchWorkflows(): Promise<Workflow[]> {
  const { data, error, response } = await serverApi.GET("/v1/workflows");
  if (error || !response.ok || !data) throwOnApiError(error, response);
  return (data as { workflows: Workflow[] }).workflows;
}

export async function fetchWorkflow(id: string): Promise<Workflow | null> {
  try {
    const { data, error, response } = await serverApi.GET("/v1/workflows/{workflow_id}", {
      params: { path: { workflow_id: id } },
    });
    if (error || !response.ok || !data) throwOnApiError(error, response);
    return (data as { workflow: Workflow }).workflow;
  } catch {
    return null;
  }
}

export async function fetchAudits() {
  const { data, error, response } = await serverApi.GET("/v1/audits");
  if (error || !response.ok || !data) throwOnApiError(error, response);
  return data as { audits: import("@/lib/types").Audit[] };
}

export async function fetchMetrics() {
  const { data, error, response } = await serverApi.GET("/v1/metrics");
  if (error || !response.ok || !data) throwOnApiError(error, response);
  return data as {
    kpis: import("@/lib/types").KpiMetric[];
    performanceSeries: import("@/lib/types").PerformancePoint[];
    violationBreakdown: import("@/lib/types").ViolationBreakdown[];
    healthAlerts?: import("@/lib/types").HealthAlert[];
  };
}

export async function fetchAuditDetail(id: string): Promise<RunAuditDetail | null> {
  try {
    const { data, error, response } = await serverApi.GET("/v1/audits/{audit_id}", {
      params: { path: { audit_id: id } },
    });
    if (error || !response.ok || !data) throwOnApiError(error, response);
    return data as RunAuditDetail;
  } catch {
    return null;
  }
}

export const fetchRulesLibrary = cache(async () => {
  const { data, error, response } = await serverApi.GET("/v1/rules/library");
  if (error || !response.ok || !data) throwOnApiError(error, response);
  return data as { rules: import("@/lib/types").RuleTemplate[] };
});
