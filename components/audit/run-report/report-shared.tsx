"use client";

import type { RunAuditField } from "@/lib/types/audit";
import { formatExtractedFieldValue } from "@/lib/utils";

export function formatFieldValue(field: RunAuditField, locale: string): string {
  if (!field.extracted) return "—";
  return formatExtractedFieldValue(field.value, field.type, locale);
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

const DEFAULT_LABELS = {
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
} satisfies RunReportLabels;

/**
 * Callers read the merged result without null checks, so the return type keeps
 * every defaulted key required and leaves the rest optional.
 */
export function mergeLabels(labels?: RunReportLabels) {
  return { ...DEFAULT_LABELS, ...labels };
}
