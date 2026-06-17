"use client";

import { ArrowRight } from "lucide-react";
import { cn } from "@/lib/utils";
import {
  isRuleFailure,
  RuleStatusIcon,
  ruleStatusColor,
  ruleStatusLabel,
} from "@/lib/rule-status";
import type { RunAuditDetail, RunAuditRule } from "@/lib/types/audit";
import { mergeLabels, type RunReportLabels } from "./report-shared";

export function RunDetailedRuleCard({
  rule,
  labels,
  size = "md",
}: {
  rule: RunAuditRule;
  labels?: RunReportLabels;
  size?: "sm" | "md";
}) {
  const L = mergeLabels(labels);
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

  const kindLabel = rule.kind === "logic" ? L.logic : L.llm;
  const scopeLabel = rule.scope === "cross" ? L.cross : L.intra;
  const sevLabel =
    rule.severity === "reject" ? L.reject : rule.severity === "flag" ? L.flag : L.info;
  const statusText = passed ? (L.statusPassed ?? L.passed) : ruleStatusLabel(rule.status);

  const pad = size === "sm" ? "px-4 py-3" : "px-5 py-4";
  const detailPad = size === "sm" ? "px-4 pb-3 pt-0 ml-7" : "px-5 pb-4 ml-8 pt-3 border-t border-border/40";

  return (
    <div className={cn("panel-elevated rounded-xl overflow-hidden", borderCls, bgCls)}>
      <div className={cn("flex items-start gap-3", pad)}>
        <RuleStatusIcon
          status={rule.status}
          className={cn(
            "h-4 w-4 shrink-0 mt-0.5",
            iconCls,
            size === "md" && "h-5 w-5"
          )}
        />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-1">
            <span className="text-sm font-semibold text-on-surface">{rule.name}</span>
            <span className="text-[10px] font-mono uppercase tracking-wide px-1.5 py-0.5 rounded bg-primary/10 text-primary">
              {kindLabel}
            </span>
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
          {rule.kind === "logic" && (
            <code className="text-[10px] font-mono text-on-surface-variant block truncate">
              {rule.expression}
            </code>
          )}
        </div>
        <span className={cn("text-xs font-semibold shrink-0 mt-0.5", passed ? "text-success" : iconCls)}>
          {statusText}
        </span>
      </div>

      {!passed && (
        <div className={cn(detailPad, "space-y-2")}>
          <p className={cn("text-on-surface leading-relaxed", size === "sm" ? "text-xs" : "text-sm")}>
            {rule.detail}
          </p>
          {(rule.expectedValue || rule.actualValue) && (
            <div className="flex items-center gap-4 flex-wrap">
              {rule.expectedValue && (
                <div className={size === "sm" ? "text-[11px]" : "text-xs"}>
                  <span className="text-on-surface-variant">{L.expected} </span>
                  <code className="font-mono font-semibold text-success">{rule.expectedValue}</code>
                </div>
              )}
              {rule.expectedValue && rule.actualValue && (
                <ArrowRight className="h-3.5 w-3.5 text-on-surface-variant shrink-0" />
              )}
              {rule.actualValue && (
                <div className={size === "sm" ? "text-[11px]" : "text-xs"}>
                  <span className="text-on-surface-variant">{L.got} </span>
                  <code className="font-mono font-semibold text-danger">{rule.actualValue}</code>
                </div>
              )}
            </div>
          )}
          {rule.affectedFields.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-1">
              {size === "md" && (
                <span className="text-[11px] text-on-surface-variant mr-2">{L.affectedFields}:</span>
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

export function RunRuleResultsSummary({
  audit,
}: {
  audit: RunAuditDetail;
}) {
  return (
    <ul className="space-y-2">
      {audit.ruleResults.map((rule) => {
        return (
          <li
            key={rule.id}
            className={cn(
              "rounded-lg border px-3 py-2 text-sm",
              isRuleFailure(rule.status) ? "border-danger/30 bg-danger/5" : "border-border bg-card"
            )}
          >
            <div className="flex items-center gap-2">
              <span className={ruleStatusColor(rule.status)}>
                <RuleStatusIcon
                  status={rule.status}
                  className="h-4 w-4"
                  aria-hidden="true"
                />
              </span>
              <span className="font-medium">{rule.name}</span>
              <span className="text-xs text-on-surface-variant ml-auto">
                {ruleStatusLabel(rule.status)}
              </span>
            </div>
            {rule.detail ? (
              <p className="text-xs text-on-surface-variant mt-1 font-mono">{rule.detail}</p>
            ) : null}
          </li>
        );
      })}
    </ul>
  );
}

export function RunRuleResultsDetailed({
  audit,
  labels,
  size = "md",
}: {
  audit: RunAuditDetail;
  labels?: RunReportLabels;
  size?: "sm" | "md";
}) {
  const failed = audit.ruleResults.filter((r) => isRuleFailure(r.status));
  const passed = audit.ruleResults.filter((r) => r.status === "passed");
  const other = audit.ruleResults.filter(
    (r) => r.status !== "passed" && !isRuleFailure(r.status)
  );
  const ordered = [...failed, ...other, ...passed];

  return (
    <>
      {ordered.map((rule) => (
        <RunDetailedRuleCard key={rule.id} rule={rule} labels={labels} size={size} />
      ))}
    </>
  );
}
