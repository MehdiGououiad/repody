"use client";

import {
  AlertTriangle,
  CheckCircle2,
  XCircle,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { RunAuditDetail } from "@/lib/types/audit";
import { formatDurationMs } from "@/lib/types/audit";
import { mergeLabels, type RunReportLabels } from "./report-shared";

export function RunStatusBanner({
  audit,
  labels,
  subtitle,
  className,
  footer,
}: {
  audit: RunAuditDetail;
  labels?: RunReportLabels;
  subtitle?: string;
  className?: string;
  footer?: React.ReactNode;
}) {
  const L = mergeLabels(labels);
  const failed = audit.status === "failed";
  const passed = audit.status === "passed";

  const cfg = passed
    ? {
        bg: "bg-success/10 border-success/30",
        icon: CheckCircle2,
        iconCls: "text-success",
        label: L.allPassed!,
        labelCls: "text-success",
      }
    : failed
      ? {
          bg: "bg-danger/10 border-danger/30",
          icon: XCircle,
          iconCls: "text-danger",
          label: L.validationFailed!,
          labelCls: "text-danger",
        }
      : {
          bg: "bg-warning/10 border-warning/30",
          icon: AlertTriangle,
          iconCls: "text-warning",
          label: L.reviewRequired!,
          labelCls: "text-warning",
        };

  const Icon = cfg.icon;

  return (
    <div className={cn("panel-elevated rounded-xl px-5 py-4 flex items-start gap-4", cfg.bg, className)}>
      <Icon className={cn("h-6 w-6 shrink-0 mt-0.5", cfg.iconCls)} />
      <div className="flex-1 min-w-0">
        <p className={cn("text-base font-bold", cfg.labelCls)}>{cfg.label}</p>
        {subtitle && (
          <p className="text-xs text-on-surface-variant mt-0.5">{subtitle}</p>
        )}
        <div className="flex flex-wrap gap-3 mt-3">
          <span className="text-[11px] bg-surface-container px-2 py-1 rounded-md text-on-surface-variant">
            <span className="font-semibold text-on-surface">{audit.summary.fieldsExtracted}</span>{" "}
            {L.fieldsExtracted ?? "fields extracted"}
          </span>
          <span className="text-[11px] bg-surface-container px-2 py-1 rounded-md text-on-surface-variant">
            {L.rulesPassed ??
              `${audit.summary.passed}/${audit.summary.total} rules passed`}
          </span>
          {audit.summary.failed > 0 && (
            <span className="text-[11px] bg-surface-container px-2 py-1 rounded-md text-on-surface-variant">
              <span className="font-semibold text-danger">{audit.summary.failed}</span>{" "}
              {L.rulesFailed ?? "failed"}
            </span>
          )}
          {footer}
        </div>
        {audit.metadata?.durationMs != null && !subtitle && (
          <span className="text-xs font-mono text-on-surface-variant mt-2 inline-block">
            {formatDurationMs(audit.metadata.durationMs)}
          </span>
        )}
      </div>
    </div>
  );
}
