"use client";

import { LoaderCircle, type LucideIcon } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import type { OperatorJob } from "@/lib/api/operator";

export const ACTIVE_STATUSES = new Set(["queued", "running"]);
export const SETTINGS_TABS = ["overview", "models", "benchmarks", "diagnostics"] as const;
export type SettingsTab = (typeof SETTINGS_TABS)[number];

export function formatDuration(ms?: number | null) {
  if (ms == null) return "-";
  return ms >= 1000 ? `${(ms / 1000).toFixed(1)}s` : `${ms}ms`;
}

export function formatPercent(value?: number | null) {
  return value == null ? "-" : `${Math.round(value * 100)}%`;
}

export function StatusBadge({ status }: { status: OperatorJob["status"] }) {
  const active = ACTIVE_STATUSES.has(status);
  return (
    <Badge
      variant={status === "completed" ? "success" : status === "failed" ? "danger" : "outline"}
      className="gap-1"
    >
      {active ? <LoaderCircle className="h-3 w-3 animate-spin" /> : null}
      {status}
    </Badge>
  );
}

export function MetricCard({
  label,
  value,
  detail,
  Icon,
}: {
  label: string;
  value: string;
  detail: string;
  Icon: LucideIcon;
}) {
  return (
    <div className="panel-elevated rounded-xl p-5 min-w-0">
      <div className="flex items-center justify-between gap-3">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-on-surface-variant">
          {label}
        </p>
        <span className="size-9 rounded-lg bg-primary/10 text-primary flex items-center justify-center">
          <Icon className="h-4 w-4" aria-hidden="true" />
        </span>
      </div>
      <p className="mt-4 text-2xl font-display font-semibold text-on-surface truncate">{value}</p>
      <p className="mt-1 text-xs text-on-surface-variant">{detail}</p>
    </div>
  );
}
