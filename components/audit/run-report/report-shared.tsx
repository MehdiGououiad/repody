"use client";

import { cn, formatExtractedFieldValue } from "@/lib/utils";
import type { RunAuditField } from "@/lib/types/audit";

export function formatFieldValue(field: RunAuditField, locale: string): string {
  if (!field.extracted) return "—";
  return formatExtractedFieldValue(field.value, field.type, locale);
}

export function ConfidenceBar({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const color = pct >= 90 ? "bg-success" : pct >= 70 ? "bg-warning" : "bg-danger";
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-20 rounded-full bg-surface-container-highest overflow-hidden">
        <div className={cn("h-full rounded-full", color)} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-[10px] font-mono text-on-surface-variant tabular-nums">{pct}%</span>
    </div>
  );
}

export type RunReportLabels = {
  allPassed?: string;
  validationFailed?: string;
  reviewRequired?: string;
  fieldsExtracted?: string;
  rulesPassed?: string;
  rulesFailed?: string;
  docExtracted?: string | ((done: number, total: number) => string);
  statusPassed?: string;
  expected?: string;
  got?: string;
  logic?: string;
  llm?: string;
  cross?: string;
  intra?: string;
  reject?: string;
  flag?: string;
  info?: string;
  passed?: string;
  affectedFields?: string;
  extractedData?: string;
  validationResults?: string;
};

export const DEFAULT_LABELS: RunReportLabels = {
  allPassed: "All rules passed",
  validationFailed: "Validation failed",
  reviewRequired: "Review required",
  statusPassed: "Passed",
  expected: "Expected",
  got: "Got",
  logic: "logic",
  llm: "llm",
  cross: "cross",
  intra: "intra",
  reject: "reject",
  flag: "flag",
  info: "info",
  passed: "Passed",
  affectedFields: "Affected fields",
  extractedData: "Extracted data",
  validationResults: "Validation results",
};

export function mergeLabels(labels?: RunReportLabels): RunReportLabels {
  return { ...DEFAULT_LABELS, ...labels };
}
