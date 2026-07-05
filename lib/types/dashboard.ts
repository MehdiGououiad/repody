/** Dashboard and audit list types. */

export type AuditStatus = "passed" | "failed" | "warning" | "running";

export interface Audit {
  id: string;
  status: AuditStatus;
  workflowId: string;
  workflowName: string;
  entity: string;
  timestamp: string;
  rows: number | null;
  failedRules?: number;
}

export interface KpiMetric {
  id: string;
  label: string;
  value: string;
  rawValue: number;
  delta: number;
  deltaUnit: "percent" | "absolute";
  direction: "up" | "down";
  positive: boolean;
  series: { day: string; value: number }[];
  icon: string;
}

export interface PerformancePoint {
  day: string;
  runs: number;
  prevRuns: number;
}

export interface ViolationBreakdown {
  type: string;
  share: number;
  color: "danger" | "warning" | "info" | "neutral";
}

export interface HealthAlert {
  id: string;
  severity: "info" | "warning" | "danger";
  titleKey: string;
  detailKey: string;
  href?: string;
}
