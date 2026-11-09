"use client";

import { useTranslations } from "next-intl";
import {
  byRuleStatus,
  isRuleFailure,
  RuleStatusIcon,
  ruleStatusColor,
} from "@/components/shared/rule-status";
import type { RunAuditDetail, RunAuditRule } from "@/lib/types";
import { cn } from "@/lib/utils";

export function RunDetailedRuleCard({
  rule,
  size = "md",
}: {
  rule: RunAuditRule;
  size?: "sm" | "md";
}) {
  const t = useTranslations("audits.report");
  const passed = rule.status === "passed";
  const failedRule = isRuleFailure(rule.status);
  const iconCls = passed ? "text-success" : ruleStatusColor(rule.status);
  const borderCls = passed
    ? "border-success/20"
    : failedRule
      ? rule.severity === "flag"
        ? "border-warning/30"
        : "border-danger/30"
      : "border-border";
  const bgCls = passed
    ? "bg-success/5"
    : failedRule
      ? rule.severity === "flag"
        ? "bg-warning/5"
        : "bg-danger/5"
      : "bg-surface-container-low/50";

  const scopeLabel = rule.scope === "cross" ? t("cross") : t("intra");
  const sevLabel = rule.severity === "reject" ? t("reject") : t("flag");
  const statusText = t(rule.status);

  const pad = size === "sm" ? "px-4 py-3" : "px-5 py-4";
  const detailPad =
    size === "sm" ? "px-4 pb-3 pt-0 ml-7" : "px-5 pb-4 ml-8 pt-3 border-t border-border/40";

  return (
    <div className={cn("panel-elevated rounded-xl overflow-hidden", borderCls, bgCls)}>
      <div className={cn("flex items-start gap-3", pad)}>
        <RuleStatusIcon
          status={rule.status}
          className={cn("h-4 w-4 shrink-0 mt-0.5", iconCls, size === "md" && "h-5 w-5")}
        />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-1">
            <span className="text-sm font-semibold text-on-surface">{rule.name}</span>
            <span className="text-[10px] font-mono uppercase tracking-wide px-1.5 py-0.5 rounded bg-surface-container text-on-surface-variant">
              {scopeLabel}
            </span>
            <span
              className={cn(
                "text-[10px] font-semibold uppercase tracking-wide px-1.5 py-0.5 rounded",
                rule.severity === "reject"
                  ? "bg-danger/10 text-danger"
                  : rule.severity === "flag"
                    ? "bg-warning/10 text-warning"
                    : "bg-surface-container text-on-surface-variant"
              )}
            >
              {sevLabel}
            </span>
          </div>
          <code className="text-[10px] font-mono text-on-surface-variant block truncate">
            {rule.expression}
          </code>
        </div>
        <span
          className={cn("text-xs font-semibold shrink-0 mt-0.5", passed ? "text-success" : iconCls)}
        >
          {statusText}
        </span>
      </div>

      {!passed && (
        <div className={cn(detailPad, "space-y-2")}>
          <p
            className={cn("text-on-surface leading-relaxed", size === "sm" ? "text-xs" : "text-sm")}
          >
            {rule.detail}
          </p>
          {rule.affectedFields.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-1">
              {size === "md" && (
                <span className="text-[11px] text-on-surface-variant mr-2">
                  {t("affectedFields")}:
                </span>
              )}
              {rule.affectedFields.map((f) => (
                <code
                  key={f}
                  className="text-[10px] font-mono bg-danger/10 text-danger px-1.5 py-0.5 rounded"
                >
                  {f}
                </code>
              ))}
            </div>
          )}
        </div>
      )}
      {passed && rule.detail && size === "md" && (
        <div className="px-5 pb-3 ml-8 border-t border-border/30 pt-2">
          <p className="text-xs text-on-surface-variant">{rule.detail}</p>
        </div>
      )}
    </div>
  );
}

export function RunRuleResultsDetailed({
  audit,
  size = "md",
}: {
  audit: RunAuditDetail;
  size?: "sm" | "md";
}) {
  return (
    <>
      {byRuleStatus(audit.ruleResults).map((rule) => (
        <RunDetailedRuleCard key={rule.id} rule={rule} size={size} />
      ))}
    </>
  );
}
