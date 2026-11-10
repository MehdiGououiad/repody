"use client";

import {
  AlertCircle,
  ArrowRight,
  CheckCircle2,
  Code,
  ExternalLink,
  FileText,
  FlaskConical,
  Loader2,
  XCircle,
} from "lucide-react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { isRuleFailure, RuleStatusIcon, ruleStatusColor } from "@/components/shared/rule-status";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { TestRunSummaryDetails } from "@/components/workflow/run-details-meta";
import { RunProgressSteps } from "@/components/workflow/run-progress-steps";
import type { RunView } from "@/lib/api/runs";
import type { RunAuditDetail } from "@/lib/types";
import { cn } from "@/lib/utils";

const statusColor: Record<RunAuditDetail["status"], string> = {
  passed: "border-success/40 bg-success/5 text-success",
  failed: "border-danger/40 bg-danger/5 text-danger",
  warning: "border-warning/40 bg-warning/5 text-warning",
};

const statusIcon: Record<RunAuditDetail["status"], typeof CheckCircle2> = {
  passed: CheckCircle2,
  failed: XCircle,
  warning: AlertCircle,
};

/** Results area of a test run: a placeholder until a run finishes (a failure shows above). */
export function TestRunResults({ run, starting }: { run: RunView; starting: boolean }) {
  const t = useTranslations("workflows.builder");
  const phase = starting ? "running" : run.phase;
  const resultsKey = run.phase === "done" ? `done-${run.result.id}` : phase;

  return (
    <section aria-live="polite" className="space-y-4 min-w-0">
      <div>
        <h3 className="text-sm font-semibold text-on-surface">{t("test.resultsTitle")}</h3>
        <p className="text-xs text-on-surface-variant mt-0.5">{t("test.resultsHint")}</p>
      </div>

      <div key={resultsKey} className="panel-reveal min-w-0">
        {phase === "idle" || phase === "failed" ? (
          <div className="rounded-xl border border-dashed border-border/80 bg-surface-container-low/40 px-4 py-6 text-center">
            <FlaskConical
              className="mx-auto h-6 w-6 text-on-surface-variant/35"
              aria-hidden="true"
            />
            <p className="mt-2 text-sm text-on-surface-variant">{t("test.idle")}</p>
            <p className="mt-1 text-xs text-on-surface-variant/70">{t("test.idleHint")}</p>
          </div>
        ) : null}

        {phase === "running" ? (
          <div className="panel-elevated rounded-xl p-4">
            {run.phase === "running" && run.progress ? (
              <RunProgressSteps progress={run.progress} />
            ) : (
              <div className="flex flex-col items-center justify-center gap-3 py-8">
                <Loader2 className="h-7 w-7 animate-spin text-accent-blue" />
                <p className="text-sm text-on-surface-variant">{t("test.progress.starting")}</p>
              </div>
            )}
          </div>
        ) : null}

        {run.phase === "done" && !starting ? <DoneResult result={run.result} /> : null}
      </div>
    </section>
  );
}

function DoneResult({ result }: { result: RunAuditDetail }) {
  const t = useTranslations("workflows.builder");
  const tReport = useTranslations("audits.report");
  const StatusIcon = statusIcon[result.status];
  return (
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
            {result.summary.fieldsExtracted} {t("test.fieldsExtracted")} {"\u00b7"}{" "}
            {result.summary.passed}/{result.summary.total} {t("test.rulesPassed")}
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
            const failedRule = isRuleFailure(rule.status);

            return (
              <div key={rule.id} className="flex items-start gap-3 px-4 py-3 min-w-0">
                <RuleStatusIcon
                  status={rule.status}
                  className={cn("h-4 w-4 shrink-0 mt-0.5", ruleStatusColor(rule.status))}
                />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1.5 flex-wrap">
                    <Code className="h-3 w-3 text-on-surface-variant shrink-0" />
                    <span className="text-xs font-semibold text-on-surface">{rule.name}</span>
                    {failedRule && rule.severity === "reject" ? (
                      <Badge variant="danger" className="text-[9px] px-1">
                        {tReport("reject")}
                      </Badge>
                    ) : null}
                    {rule.status === "skipped" ? (
                      <Badge variant="secondary" className="text-[9px] px-1">
                        {tReport(rule.status)}
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
  );
}
