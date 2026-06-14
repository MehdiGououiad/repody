"use client";

import { useTranslations } from "next-intl";
import {
  AlertCircle,
  CheckCircle2,
  AlertTriangle,
  Brain,
  Code,
  MessageSquare,
  Sparkles,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useCrossHighlight } from "@/lib/stores/cross-highlight";
import { cn } from "@/lib/utils";
import type { AuditDetail, RuleEvaluation } from "@/lib/types";

export function ComplianceRulesList({ audit }: { audit: AuditDetail }) {
  const tPanel = useTranslations("audits.detail.panels");
  const tRule = useTranslations("audits.detail.rule");
  const tRules = useTranslations("workflows.builder.rules");
  const { selectedRuleId, setSelectedRule } = useCrossHighlight();
  const passed = audit.rules.filter((r) => r.status === "passed").length;
  const failed = audit.rules.filter((r) => r.status === "failed").length;
  const warning = audit.rules.filter((r) => r.status === "warning").length;

  const statusVariant: Record<
    RuleEvaluation["status"],
    "success" | "danger" | "warning" | "secondary"
  > = {
    passed: "success",
    failed: "danger",
    warning: "warning",
    skipped: "secondary",
    error: "warning",
  };

  return (
    <div className="flex flex-col h-full bg-card">
      <div className="flex items-center justify-between px-4 py-2 border-b border-border bg-surface-container-low shrink-0">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-on-surface-variant">
          {tPanel("rules")}
        </h3>
        <div className="flex items-center gap-1.5">
          {failed > 0 ? <Badge variant="danger">{failed} {tRule("failed")}</Badge> : null}
          {warning > 0 ? <Badge variant="warning">{warning} {tRule("warning")}</Badge> : null}
          <Badge variant="success">{passed} {tRule("passed")}</Badge>
        </div>
      </div>
      <div className="flex-1 overflow-auto p-4 flex flex-col gap-3">
        {audit.rules.map((r) => {
          const isLlm = r.kind === "llm";
          const KindIcon = isLlm ? Brain : Code;
          const isSelected = selectedRuleId === r.id;
          const isFailed = r.status === "failed" || r.status === "error";
          const isPassed = r.status === "passed";
          const isSkipped = r.status === "skipped";
          return (
            <div
              key={r.id}
              role="button"
              tabIndex={0}
              onClick={() => setSelectedRule(r.id)}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  setSelectedRule(r.id);
                }
              }}
              aria-pressed={isSelected}
              className={cn(
                "border rounded-lg p-4 cursor-pointer transition-[border-color,background-color,box-shadow] relative overflow-hidden text-left w-full",
                isFailed && !isSelected && "border-danger/40 bg-danger-soft/30",
                isFailed && isSelected && "border-danger bg-danger-soft/50 shadow-sm",
                !isFailed && isSelected && "border-accent-blue bg-accent-blue/5",
                !isFailed && !isSelected && !isSkipped && "border-border hover:border-outline-variant",
                isSkipped && !isSelected && "border-border bg-surface-container-low/50 opacity-80",
                isLlm && "border-l-4 border-l-accent-blue"
              )}
            >
              {isFailed ? (
                <span className="absolute left-0 top-0 bottom-0 w-1 bg-danger" />
              ) : null}
              <div className="flex items-start gap-3">
                <div className="mt-0.5">
                  {isPassed ? (
                    <CheckCircle2 className="h-4 w-4 text-success" />
                  ) : isFailed ? (
                    <AlertCircle className="h-4 w-4 text-danger" />
                  ) : (
                    <AlertTriangle className="h-4 w-4 text-warning-strong" />
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                    <KindIcon
                      className={cn(
                        "h-3.5 w-3.5",
                        isLlm ? "text-accent-blue" : "text-on-surface-variant"
                      )}
                    />
                    <h4 className="text-sm font-semibold text-on-surface">{r.name}</h4>
                    <Badge variant={statusVariant[r.status]} className="text-[10px] py-0">
                      {r.status === "skipped" || r.status === "error"
                        ? r.status
                        : tRule(r.status)}
                    </Badge>
                    <Badge variant={isLlm ? "info" : "secondary"} className="text-[9px] gap-0.5">
                      {isLlm ? <Sparkles className="h-2.5 w-2.5" /> : null}
                      {isLlm ? tRules("kindLlm") : tRules("kindLogic")}
                    </Badge>
                    {r.severity === "reject" ? (
                      <Badge variant="outline" className="text-[10px] py-0 text-danger border-danger/30">
                        {tRule("rejectOnFail")}
                      </Badge>
                    ) : (
                      <Badge variant="outline" className="text-[10px] py-0 text-warning-strong border-warning/30">
                        {tRule("flagForReview")}
                      </Badge>
                    )}
                  </div>
                  <p
                    className={cn(
                      "text-sm",
                      isFailed ? "text-danger-strong" : "text-on-surface-variant"
                    )}
                  >
                    {r.description}
                  </p>
                  {isFailed && (r.expectedValue || r.actualValue) ? (
                    <div className="mt-3 grid grid-cols-2 gap-3 text-xs">
                      <div className="bg-card border border-border rounded p-2">
                        <div className="uppercase tracking-wider text-on-surface-variant text-[10px] font-semibold mb-1">
                          {tRule("expected")}
                        </div>
                        <div className="font-mono text-on-surface">{r.expectedValue}</div>
                      </div>
                      <div className="bg-card border border-danger/40 rounded p-2">
                        <div className="uppercase tracking-wider text-danger-strong text-[10px] font-semibold mb-1">
                          {tRule("extracted")}
                        </div>
                        <div className="font-mono text-danger-strong">{r.actualValue}</div>
                      </div>
                    </div>
                  ) : null}
                  {isFailed && r.detail ? (
                    <p className="text-xs text-on-surface-variant mt-2">{r.detail}</p>
                  ) : null}
                  {isFailed ? (
                    <div className="flex gap-2 mt-3">
                      <Button size="sm" variant="outline">
                        {tRule("overrideWithCalculated")}
                      </Button>
                      <Button size="sm" variant="ghost">
                        <MessageSquare className="h-3.5 w-3.5" />
                        {tRule("flagForManualReview")}
                      </Button>
                    </div>
                  ) : null}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
