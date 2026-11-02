import { AlertTriangle, CheckCircle2, CircleDashed, type LucideProps, XCircle } from "lucide-react";

export function RuleStatusIcon({ status, ...props }: { status: string } & LucideProps) {
  if (status === "passed") return <CheckCircle2 {...props} />;
  if (status === "failed") return <XCircle {...props} />;
  if (status === "skipped") return <CircleDashed {...props} />;
  return <AlertTriangle {...props} />;
}

export function ruleStatusColor(status: string): string {
  if (status === "passed") return "text-success";
  if (status === "failed") return "text-danger";
  if (status === "skipped") return "text-on-surface-variant";
  if (status === "error") return "text-warning";
  return "text-warning";
}

export function ruleStatusLabel(status: string): string {
  if (status === "passed") return "Passed";
  if (status === "failed") return "Failed";
  if (status === "skipped") return "Skipped";
  if (status === "error") return "Error";
  return "Warning";
}

export function isRuleFailure(status: string): boolean {
  return status === "failed" || status === "error";
}
