import type {
  ApprovalTask,
  AuditChainVerification,
  CaseRecord,
  FourEyesDecision,
  PipelineRun,
  PipelineStageInput,
} from "./types";

async function readError(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === "string" && body.detail.trim()) return body.detail;
  } catch {
    // Ignore non-JSON bodies.
  }
  return `HTTP ${response.status}`;
}

export async function createCase(
  payload: { external_ref?: string | null; input_payload: Record<string, unknown> },
  headers?: HeadersInit,
): Promise<CaseRecord> {
  const res = await fetch("/api/core/v1/cases", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...headers },
    body: JSON.stringify({ ...payload, artifacts: [] }),
  });
  if (!res.ok) throw new Error(await readError(res));
  return (await res.json()) as CaseRecord;
}

export async function startPipeline(
  caseId: string,
  stages: PipelineStageInput[],
): Promise<PipelineRun> {
  const res = await fetch(`/api/core/v1/cases/${encodeURIComponent(caseId)}/pipelines`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ stages }),
  });
  if (!res.ok) throw new Error(await readError(res));
  return (await res.json()) as PipelineRun;
}

export async function createApproval(
  payload: {
    case_id: string;
    stage_name: string;
    payload_snapshot: Record<string, unknown>;
  },
  headers?: HeadersInit,
): Promise<ApprovalTask> {
  const res = await fetch("/api/core/v1/approvals", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...headers },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await readError(res));
  return (await res.json()) as ApprovalTask;
}

export async function fetchApproval(approvalId: string): Promise<ApprovalTask> {
  const res = await fetch(`/api/core/v1/approvals/${encodeURIComponent(approvalId)}`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error(await readError(res));
  return (await res.json()) as ApprovalTask;
}

export async function submitMakerReview(
  approvalId: string,
  payload: {
    overrides: Array<{ field_path: string; after_value: unknown; reason: string }>;
    note: string;
  },
  headers?: HeadersInit,
): Promise<ApprovalTask> {
  const res = await fetch(`/api/core/v1/approvals/${encodeURIComponent(approvalId)}/make`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...headers },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await readError(res));
  return (await res.json()) as ApprovalTask;
}

export async function submitCheckerDecision(
  approvalId: string,
  payload: { decision: FourEyesDecision; note: string },
  headers?: HeadersInit,
): Promise<ApprovalTask> {
  const res = await fetch(`/api/core/v1/approvals/${encodeURIComponent(approvalId)}/check`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...headers },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await readError(res));
  return (await res.json()) as ApprovalTask;
}

export async function verifyAuditChain(): Promise<AuditChainVerification> {
  const res = await fetch("/api/core/v1/audit-events/verify", { cache: "no-store" });
  if (!res.ok) throw new Error(await readError(res));
  return (await res.json()) as AuditChainVerification;
}
