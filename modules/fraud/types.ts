export type FraudSeverity = "clean" | "low" | "medium" | "high" | "critical";

export type ArtifactKind =
  | "source_document"
  | "pdf_revision_diff"
  | "forensic_heatmap"
  | "browser_screenshot"
  | "playwright_trace"
  | "json_report";

export type ArtifactRef = {
  artifact_id: string;
  module: "core" | "idp" | "fraud" | "operator";
  kind: ArtifactKind;
  storage_key: string;
  sha256: string;
  mime_type: string;
  byte_size: number;
};

export type FraudFinding = {
  detector: string;
  tier: 1 | 2 | 3;
  code: string;
  severity: FraudSeverity;
  title: string;
  detail: string;
  page?: number | null;
  bbox?: [number, number, number, number] | null;
  evidence_artifact_id?: string | null;
};

export type FraudAnalysis = {
  id: string;
  case_id: string | null;
  account_id: string | null;
  mode: "standalone" | "pre_check" | "post_verify";
  risk_score: number;
  severity: FraudSeverity;
  short_circuit_recommended: boolean;
  requires_four_eyes: boolean;
  findings: FraudFinding[];
  generated_artifacts: ArtifactRef[];
  explanation: string | null;
  created_at: string;
};
