import {
  CheckCircle2,
  CircleDashed,
  type LucideIcon,
  type LucideProps,
  XCircle,
} from "lucide-react";
import type { RuleStatus } from "@/lib/types";

const ICON: Record<RuleStatus, LucideIcon> = {
  passed: CheckCircle2,
  failed: XCircle,
  skipped: CircleDashed,
};

const COLOR: Record<RuleStatus, string> = {
  passed: "text-success",
  failed: "text-danger",
  skipped: "text-on-surface-variant",
};

export function RuleStatusIcon({ status, ...props }: { status: RuleStatus } & LucideProps) {
  const Icon = ICON[status];
  return <Icon {...props} />;
}

export function ruleStatusColor(status: RuleStatus): string {
  return COLOR[status];
}

export function isRuleFailure(status: RuleStatus): boolean {
  return status === "failed";
}

const ORDER: Record<RuleStatus, number> = { failed: 0, skipped: 1, passed: 2 };

/** Failed rules first, then skipped, then passed; the run's order within each. */
export function byRuleStatus<T extends { status: RuleStatus }>(rules: T[]): T[] {
  return [...rules].sort((a, b) => ORDER[a.status] - ORDER[b.status]);
}
