"use client";

import Link from "next/link";
import { ChevronLeft, ExternalLink } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import {
  RunDetailedReportSections,
  RunStatusBanner,
  type RunReportLabels,
} from "@/components/audit/run-report/run-report-core";
import type { RunAuditDetail } from "@/lib/types/audit";

export type ApiRunReport = RunAuditDetail & { processedAt: string };

function apiReportLabels(
  t: ReturnType<typeof useTranslations>,
  report?: ApiRunReport
): RunReportLabels {
  return {
    allPassed: t("allPassed"),
    validationFailed: t("validationFailed"),
    reviewRequired: t("reviewRequired"),
    fieldsExtracted: report
      ? t("fieldsExtracted", { count: report.summary.fieldsExtracted })
          .replace(String(report.summary.fieldsExtracted), "")
          .trim()
      : undefined,
    rulesPassed: report
      ? t("rulesPassed", { passed: report.summary.passed, total: report.summary.total })
      : undefined,
    rulesFailed: report
      ? t("rulesFailed", { count: report.summary.failed }).replace(String(report.summary.failed), "").trim()
      : undefined,
    docExtracted: (done, total) => t("docExtracted", { done, total }),
    statusPassed: t("statusPassed"),
    expected: t("expected"),
    got: t("got"),
    extractedData: t("extractedData"),
    validationResults: t("validationResults"),
  };
}

export function ApiRunReportScreen({
  report,
  onBack,
}: {
  report: ApiRunReport;
  onBack: () => void;
}) {
  const t = useTranslations("workflows.builder.api");
  const locale = useLocale();
  const labels = apiReportLabels(t, report);
  const ts = new Date(report.processedAt).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });

  return (
    <div className="flex flex-col gap-5">
      <button
        onClick={onBack}
        className="flex items-center gap-1.5 text-xs text-on-surface-variant hover:text-on-surface transition-colors self-start"
      >
        <ChevronLeft className="h-3.5 w-3.5" />
        {t("backToApi")}
      </button>

      <RunStatusBanner
        audit={report}
        labels={labels}
        subtitle={`${report.workflowName} \u00b7 ${ts}`}
      />

      <Link
        href={`/audits/${report.id}`}
        className="flex items-center justify-between w-full rounded-xl border border-accent-blue/30 bg-accent-blue/5 hover:bg-accent-blue/10 transition-colors px-4 py-3 group"
      >
        <div>
          <p className="text-sm font-semibold text-primary">{t("viewFullReport")}</p>
          <p className="text-xs text-on-surface-variant mt-0.5">
            {report.id} \u00b7 {t("shareable")}
          </p>
        </div>
        <ExternalLink className="h-4 w-4 text-primary shrink-0 group-hover:translate-x-0.5 transition-transform" />
      </Link>

      <RunDetailedReportSections audit={report} locale={locale} labels={labels} />
    </div>
  );
}
