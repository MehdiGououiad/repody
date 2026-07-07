import { cache } from "react";
import type { Audit, RuleTemplate, Workflow } from "@/lib/types";
import type { RunAuditDetail } from "@/lib/types/audit";
import type { AuditListResponse } from "@/lib/api/schema-types";
import { serverApi, throwOnApiError } from "@/lib/api/openapi-client";

export type AuditListResult = Omit<AuditListResponse, "audits"> & {
  audits: Audit[];
};

export const fetchWorkflows = cache(async (): Promise<Workflow[]> => {
  const { data, error, response } = await serverApi.GET("/v1/workflows");
  if (error || !response.ok || !data) throwOnApiError(error, response);
  return (data as { workflows: Workflow[] }).workflows;
});

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

export const fetchAudits = cache(async (limit = 200, offset = 0): Promise<AuditListResult> => {
  const { data, error, response } = await serverApi.GET("/v1/audits", {
    params: { query: { limit, offset } },
  });
  if (error || !response.ok || !data) throwOnApiError(error, response);
  return {
    total: data.total,
    limit: data.limit,
    offset: data.offset,
    audits: data.audits as Audit[],
  };
});

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
  return data as { rules: RuleTemplate[] };
});
