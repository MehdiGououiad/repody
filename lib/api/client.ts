import { cache } from "react";
import { unwrap } from "@/lib/api/openapi-client";
import { serverApi } from "@/lib/api/openapi-server";
import type { AuditListResponse } from "@/lib/api/schema-types";
import type { Workflow } from "@/lib/types";
import type { RunAuditDetail } from "@/lib/types/audit";

export const fetchWorkflows = cache(async (): Promise<Workflow[]> => {
  const data = await unwrap(serverApi.GET("/v1/workflows"));
  return data.workflows;
});

export async function fetchWorkflow(id: string): Promise<Workflow | null> {
  try {
    return await unwrap(
      serverApi.GET("/v1/workflows/{workflow_id}", { params: { path: { workflow_id: id } } })
    );
  } catch {
    return null;
  }
}

export const fetchAudits = cache(
  (limit = 200, offset = 0): Promise<AuditListResponse> =>
    unwrap(serverApi.GET("/v1/audits", { params: { query: { limit, offset } } }))
);

export async function fetchAuditDetail(id: string): Promise<RunAuditDetail | null> {
  try {
    return await unwrap(serverApi.GET("/v1/audits/{run_id}", { params: { path: { run_id: id } } }));
  } catch {
    return null;
  }
}
