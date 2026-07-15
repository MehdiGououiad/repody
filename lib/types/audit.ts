/** Audit run DTOs — aligned with backend schemas/run.py */

export interface RunAuditField {
  key: string;
  description: string;
  value: string;
  type: string;
  confidence: number | null;
  extracted: boolean;
  flagged: boolean;
}

export interface RunDocumentExtractionMeta {
  readPathConfig: string;
  readPathUsed: string;
  readPathLabel: string;
  validationMode: string;
  validationLabel: string;
  documentModelId?: string | null;
  extractionMs: number;
  cacheHit: boolean;
  gpuColdStartLikely?: boolean;
  fieldsExtracted: number;
  markdownText?: string | null;
  rawText?: string | null;
  markdownExtraction?: boolean;
  pagesRendered?: number | null;
  pagesSent?: number | null;
  pagesDropped?: number | null;
}

export interface RunAuditDocument {
  id: string;
  documentType: string;
  fileName?: string | null;
  fields: RunAuditField[];
  extraction?: RunDocumentExtractionMeta | null;
}

export interface RunAuditRule {
  id: string;
  name: string;
  kind: "logic" | "llm";
  scope: string;
  status: "passed" | "failed" | "skipped" | "error";
  severity: "reject" | "flag" | "info";
  expression: string;
  affectedFields: string[];
  detail: string;
  expectedValue?: string;
  actualValue?: string;
}

export interface RunAuditMetadata {
  startedAt?: string | null;
  finishedAt?: string | null;
  durationMs: number;
  extractionMs: number;
  validationMs: number;
  validationMode: string;
  validationLabel: string;
  llmModel?: string | null;
}

export interface RunAuditDetail {
  id: string;
  workflowId: string;
  workflowName: string;
  status: "passed" | "failed" | "warning";
  source: "api" | "interface" | "test";
  createdAt: string;
  documents: RunAuditDocument[];
  ruleResults: RunAuditRule[];
  summary: {
    total: number;
    passed: number;
    failed: number;
    fieldsExtracted: number;
  };
  metadata?: RunAuditMetadata | null;
}

export function formatDurationMs(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  const s = ms / 1000;
  if (s < 60) return `${s.toFixed(1)}s`;
  const m = Math.floor(s / 60);
  const rem = Math.round(s % 60);
  return `${m}m ${rem}s`;
}
