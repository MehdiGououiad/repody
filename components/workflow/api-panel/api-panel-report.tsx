"use client";

import { ChevronLeft, ExternalLink } from "lucide-react";
import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { RunStatusBanner } from "@/components/audit/run-report/report-banner";
import { RunDetailedReportSections } from "@/components/audit/run-report/report-sections";
import type { RunAuditDetail } from "@/lib/types";
import { formatDateTime } from "@/lib/utils";

export function ApiRunReportScreen({
  report,
  onBack,
}: {
  report: RunAuditDetail;
  onBack: () => void;
}) {
  const t = useTranslations("workflows.builder.api");
  const locale = useLocale();

  return (
    <div className="flex flex-col gap-5">
      <button
        type="button"
        onClick={onBack}
        className="flex items-center gap-1.5 text-xs text-on-surface-variant hover:text-on-surface transition-colors self-start"
      >
        <ChevronLeft className="h-3.5 w-3.5" />
        {t("backToApi")}
      </button>

      <RunStatusBanner
        audit={report}
        subtitle={`${report.workflowName} · ${formatDateTime(report.createdAt, locale)}`}
      />

      <Link
        href={`/audits/${report.id}`}
        className="flex items-center justify-between w-full rounded-xl border border-accent-blue/30 bg-accent-blue/5 hover:bg-accent-blue/10 transition-colors px-4 py-3 group"
      >
        <div>
          <p className="text-sm font-semibold text-primary">{t("viewFullReport")}</p>
          <p className="text-xs text-on-surface-variant mt-0.5">
            {report.id} · {t("shareable")}
          </p>
        </div>
        <ExternalLink className="h-4 w-4 text-primary shrink-0 group-hover:translate-x-0.5 transition-transform" />
      </Link>

      <RunDetailedReportSections audit={report} />
    </div>
  );
}
