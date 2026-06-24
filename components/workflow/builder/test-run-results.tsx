"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import {
  AlertCircle,
  ArrowRight,
  Brain,
  CheckCircle2,
  Code,
  ExternalLink,
  FileText,
  FlaskConical,
  Loader2,
  XCircle,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { RunProgressSteps } from "@/components/workflow/run-progress-steps";
import { TestRunSummaryDetails } from "@/components/workflow/run-details-meta";
import { cn } from "@/lib/utils";
import {
  isRuleFailure,
  RuleStatusIcon,
  ruleStatusColor,
  ruleStatusLabel,
} from "@/lib/rule-status";
import type { RunProgress, TestRunResult } from "@/lib/api/workflow-run";
import type { TestPhase } from "@/components/workflow/builder/test-run-session";

const statusColor = {
  passed: "border-success/40 bg-success/5 text-success",
  failed: "border-danger/40 bg-danger/5 text-danger",
  warning: "border-warning/40 bg-warning/5 text-warning",
} as const;

export function TestRunResults({
  phase,
  progress,
  result,
}: {
  phase: TestPhase;
  progress: RunProgress | null;
  result: TestRunResult | null;
}) {
  const t = useTranslations("workflows.builder");
  const StatusIcon =
    result?.status === "passed"
      ? CheckCircle2
      : result?.status === "failed"
        ? XCircle
        : AlertCircle;
  const resultsKey = phase === "done" && result ? `done-${result.id}` : phase;

  return (
    <section aria-live="polite" className="space-y-4 min-w-0">
      <div>
        <h3 className="text-sm font-semibold text-on-surface">{t("test.resultsTitle")}</h3>
        <p className="text-xs text-on-surface-variant mt-0.5">{t("test.resultsHint")}</p>
      </div>

      <div key={resultsKey} className="panel-reveal min-w-0">
        {phase === "idle" && !result ? (
          <div className="rounded-xl border border-dashed border-border/80 bg-surface-container-low/40 px-4 py-6 text-center">
            <FlaskConical className="mx-auto h-6 w-6 text-on-surface-variant/35" aria-hidden="true" />
            <p className="mt-2 text-sm text-on-surface-variant">{t("test.idle")}</p>
            <p className="mt-1 text-xs text-on-surface-variant/70">{t("test.idleHint")}</p>
          </div>
        ) : null}

        {phase === "running" ? (
          <div className="panel-elevated rounded-xl p-4">
            {progress ? (
              <RunProgressSteps progress={progress} />
            ) : (
              <div className="flex flex-col items-center justify-center gap-3 py-8">
                <Loader2 className="h-7 w-7 animate-spin text-accent-blue" />
                <p className="text-sm text-on-surface-variant">{t("test.progress.starting")}</p>
              </div>
            )}
          </div>
        ) : null}

        {phase === "done" && result ? (
          <div className="space-y-4 min-w-0">
            <div
              className={cn(
                "panel-elevated rounded-xl p-4 flex flex-wrap items-center gap-3",
                statusColor[result.status]
              )}
            >
              <StatusIcon className="h-5 w-5 shrink-0" />
              <div className="flex-1 min-w-[12rem]">
                <p className="text-sm font-semibold">{t(`test.status.${result.status}`)}</p>
                <p className="text-xs opacity-80 mt-0.5">
                  {result.summary.fieldsExtracted} {t("test.fieldsExtracted")}{" "}
                  {"\u00b7"} {result.summary.passed}/{result.summary.total}{" "}
                  {t("test.rulesPassed")}
                </p>
              </div>
              <Link href={`/audits/${result.id}`} className="shrink-0" target="_blank">
                <Button variant="outline" size="sm" className="gap-1.5 h-8 text-xs">
                  {t("test.viewReport")}
                  <ExternalLink className="h-3 w-3" />
                </Button>
              </Link>
            </div>

            <TestRunSummaryDetails result={result} />

            <div className="panel-elevated rounded-xl overflow-hidden min-w-0">
              <div className="px-4 py-2.5 bg-surface-container-low border-b border-border">
                <p className="text-[11px] font-semibold uppercase tracking-wider text-on-surface-variant">
                  {t("test.ruleResults")}
                </p>
              </div>
              <div className="divide-y divide-border">
                {result.ruleResults.map((rule) => {
                  const KindIcon = rule.kind === "llm" ? Brain : Code;
                  const failedRule = isRuleFailure(rule.status);

                  return (
                    <div key={rule.id} className="flex items-start gap-3 px-4 py-3 min-w-0">
                      <RuleStatusIcon
                        status={rule.status}
                        className={cn(
                          "h-4 w-4 shrink-0 mt-0.5",
                          ruleStatusColor(rule.status)
                        )}
                      />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-1.5 flex-wrap">
                          <KindIcon className="h-3 w-3 text-on-surface-variant shrink-0" />
                          <span className="text-xs font-semibold text-on-surface">{rule.name}</span>
                          {failedRule && rule.severity === "reject" ? (
                            <Badge variant="danger" className="text-[9px] px-1">
                              Reject
                            </Badge>
                          ) : null}
                          {rule.status !== "passed" && rule.status !== "failed" ? (
                            <Badge variant="secondary" className="text-[9px] px-1">
                              {ruleStatusLabel(rule.status)}
                            </Badge>
                          ) : null}
                        </div>
                        <p
                          className={cn(
                            "text-[11px] mt-0.5 leading-relaxed break-words",
                            failedRule ? "text-danger-strong" : "text-on-surface-variant"
                          )}
                        >
                          {rule.detail}
                        </p>
                      </div>
                    </div>
                  );
                })}
                {result.ruleResults.length === 0 ? (
                  <p className="px-4 py-6 text-sm text-on-surface-variant text-center">
                    {t("test.noRules")}
                  </p>
                ) : null}
              </div>
            </div>

            <Link href={`/audits/${result.id}`} target="_blank">
              <Button variant="outline" className="w-full gap-2 h-9">
                <FileText className="h-4 w-4" />
                {t("test.openFullReport")}
                <ArrowRight className="h-3.5 w-3.5 ml-auto" />
              </Button>
            </Link>
          </div>
        ) : null}
      </div>
    </section>
  );
}
