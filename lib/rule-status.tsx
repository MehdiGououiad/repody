import {
  AlertTriangle,
  CheckCircle2,
  CircleDashed,
  XCircle,
  type LucideProps,
} from "lucide-react";

export type RuleEvalStatus =
  | "passed"
  | "failed"
  | "skipped"
  | "error"
  | "warning";

export function RuleStatusIcon({
  status,
  ...props
}: { status: RuleEvalStatus } & LucideProps) {
  if (status === "passed") return <CheckCircle2 {...props} />;
  if (status === "failed") return <XCircle {...props} />;
  if (status === "skipped") return <CircleDashed {...props} />;
  return <AlertTriangle {...props} />;
}

export function ruleStatusColor(status: RuleEvalStatus): string {
  if (status === "passed") return "text-success";
  if (status === "failed") return "text-danger";
  if (status === "skipped") return "text-on-surface-variant";
  if (status === "error") return "text-warning";
  return "text-warning";
}

export function ruleStatusBorder(status: RuleEvalStatus): string {
  if (status === "passed") return "border-success/40";
  if (status === "failed") return "border-danger/40";
  if (status === "skipped") return "border-border";
  if (status === "error") return "border-warning/40";
  return "border-warning/30";
}

export function ruleStatusLabel(status: RuleEvalStatus): string {
  if (status === "passed") return "Passed";
  if (status === "failed") return "Failed";
  if (status === "skipped") return "Skipped";
  if (status === "error") return "Error";
  return "Warning";
}

export function isRuleFailure(status: RuleEvalStatus): boolean {
  return status === "failed" || status === "error";
}
