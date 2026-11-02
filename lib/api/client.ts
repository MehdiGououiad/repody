import { cache } from "react";
import { throwOnApiError } from "@/lib/api/openapi-client";
import { serverApi } from "@/lib/api/openapi-server";
import type { AuditListResponse } from "@/lib/api/schema-types";
import { workflowFromWire } from "@/lib/api/workflow-wire";
import type { RuleTemplate, Workflow } from "@/lib/types";
import type { RunAuditDetail } from "@/lib/types/audit";

export const fetchWorkflows = cache(async (): Promise<Workflow[]> => {
  const { data, error, response } = await serverApi.GET("/v1/workflows");
  if (error || !response.ok || !data) throwOnApiError(error, response);
  return data.workflows.map(workflowFromWire);
});

export async function fetchWorkflow(id: string): Promise<Workflow | null> {
  try {
    const { data, error, response } = await serverApi.GET("/v1/workflows/{workflow_id}", {
      params: { path: { workflow_id: id } },
    });
    if (error || !response.ok || !data) throwOnApiError(error, response);
    return workflowFromWire(data.workflow);
  } catch {
    return null;
  }
}

export const fetchAudits = cache(async (limit = 200, offset = 0): Promise<AuditListResponse> => {
  const { data, error, response } = await serverApi.GET("/v1/audits", {
    params: { query: { limit, offset } },
  });
  if (error || !response.ok || !data) throwOnApiError(error, response);
  return data;
});

export async function fetchAuditDetail(id: string): Promise<RunAuditDetail | null> {
  try {
    const { data, error, response } = await serverApi.GET("/v1/audits/{audit_id}", {
      params: { path: { audit_id: id } },
    });
    if (error || !response.ok || !data) throwOnApiError(error, response);
    return data;
  } catch {
    return null;
  }
}

export const fetchRulesLibrary = cache(async () => {
  const { data, error, response } = await serverApi.GET("/v1/rules/library");
  if (error || !response.ok || !data) throwOnApiError(error, response);
  return data as { rules: RuleTemplate[] };
});
