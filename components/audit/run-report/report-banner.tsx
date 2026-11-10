"use client";

import { AlertTriangle, CheckCircle2, XCircle } from "lucide-react";
import { useTranslations } from "next-intl";
import type { RunAuditDetail } from "@/lib/types";
import { cn, formatDurationMs } from "@/lib/utils";

export function RunStatusBanner({
  audit,
  subtitle,
  className,
  footer,
}: {
  audit: RunAuditDetail;
  subtitle?: React.ReactNode;
  className?: string;
  footer?: React.ReactNode;
}) {
  const t = useTranslations("audits.report");
  const failed = audit.status === "failed";
  const passed = audit.status === "passed";

  const cfg = passed
    ? {
        bg: "bg-success/10 border-success/30",
        icon: CheckCircle2,
        iconCls: "text-success",
        label: t("allRulesPassed"),
        labelCls: "text-success",
      }
    : failed
      ? {
          bg: "bg-danger/10 border-danger/30",
          icon: XCircle,
          iconCls: "text-danger",
          label: t("validationFailed"),
          labelCls: "text-danger",
        }
      : {
          bg: "bg-warning/10 border-warning/30",
          icon: AlertTriangle,
          iconCls: "text-warning",
          label: t("reviewRequired"),
          labelCls: "text-warning",
        };

  const Icon = cfg.icon;

  return (
    <div
      className={cn(
        "panel-elevated rounded-xl px-5 py-4 flex items-start gap-4",
        cfg.bg,
        className
      )}
    >
      <Icon className={cn("h-6 w-6 shrink-0 mt-0.5", cfg.iconCls)} />
      <div className="flex-1 min-w-0">
        <p className={cn("text-base font-bold", cfg.labelCls)}>{cfg.label}</p>
        {subtitle && <p className="text-xs text-on-surface-variant mt-0.5">{subtitle}</p>}
        <div className="flex flex-wrap gap-3 mt-3">
          <span className="text-[11px] bg-surface-container px-2 py-1 rounded-md text-on-surface-variant">
            {t("fieldsExtracted", { count: audit.summary.fieldsExtracted })}
          </span>
          <span className="text-[11px] bg-surface-container px-2 py-1 rounded-md text-on-surface-variant">
            {t("rulesPassed", { passed: audit.summary.passed, total: audit.summary.total })}
          </span>
          {audit.summary.failed > 0 && (
            <span className="text-[11px] bg-surface-container px-2 py-1 rounded-md text-on-surface-variant">
              {t("rulesFailed", { count: audit.summary.failed })}
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
