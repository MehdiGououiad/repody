export type CaseStatus =
  | "open"
  | "in_progress"
  | "waiting_maker"
  | "waiting_checker"
  | "approved"
  | "rejected"
  | "failed";

export type ApprovalStatus =
  | "waiting_maker"
  | "waiting_checker"
  | "approved"
  | "rejected"
  | "returned_to_maker";

export type FourEyesDecision = "approved" | "rejected" | "returned_to_maker";

export type CaseArtifact = {
  id: string;
  case_id: string;
  module: "core" | "idp" | "fraud" | "operator";
  kind: string;
  storage_key: string;
  sha256: string;
  mime_type: string;
  byte_size: number;
  created_at: string;
};

export type CaseRecord = {
  id: string;
  account_id: string | null;
  external_ref: string | null;
  input_payload: Record<string, unknown>;
  status: CaseStatus;
  created_by: string;
  created_at: string;
  updated_at: string;
  artifacts: CaseArtifact[];
};

export type FieldOverrideRecord = {
  id: string;
  case_id: string;
  approval_task_id: string;
  field_path: string;
  before_value: unknown;
  after_value: unknown;
  actor_sub: string;
  reason: string;
  created_at: string;
};

export type ApprovalTask = {
  id: string;
  case_id: string;
  stage_name: string;
  status: ApprovalStatus;
  payload_snapshot: Record<string, unknown>;
  payload_sha256: string;
  maker_sub: string | null;
  maker_note: string;
  maker_decided_at: string | null;
  checker_sub: string | null;
  checker_note: string;
  checker_decided_at: string | null;
  created_at: string;
  updated_at: string;
  overrides: FieldOverrideRecord[];
};

export type PipelineStageInput =
  | { kind: "fraud_pre_check"; short_circuit_on_critical?: boolean }
  | { kind: "idp"; workflow_id: string }
  | { kind: "fraud_post_verify" }
  | { kind: "four_eyes_gate"; approval_id?: string | null; stage_name?: string };

export type PipelineRun = {
  id: string;
  case_id: string;
  stages: Array<Record<string, unknown>>;
  status: string;
  hatchet_run_id: string | null;
  created_at: string;
  finished_at: string | null;
};

export type AuditChainVerification = {
  valid: boolean;
  checked_count: number;
  first_broken_id: string | null;
};
