"use client";

import { ChevronLeft, Download, FileText, Printer, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { useNow, useTranslations } from "next-intl";
import { RunStatusBanner } from "@/components/audit/run-report/report-banner";
import { ReportDocument } from "@/components/audit/run-report/report-document";
import { RunDetailedRuleCard } from "@/components/audit/run-report/report-rules";
import { DateTime } from "@/components/shared/date-time";
import { byRuleStatus } from "@/components/shared/rule-status";
import { Button } from "@/components/ui/button";
import { RunMetadataPanel } from "@/components/workflow/run-details-meta";
import type { RunAuditDetail } from "@/lib/types";

/** The full audit report of one finished run; prints as a PDF, exports as CSV (from the API). */
export function RunAuditReport({ audit }: { audit: RunAuditDetail }) {
  const t = useTranslations("audits.report");
  const now = useNow();
  const ranAt = (
    <DateTime value={audit.createdAt} format={{ dateStyle: "long", timeStyle: "short" }} />
  );
  const via = audit.source === "api" ? t("api") : t("interface");

  return (
    <div className="min-h-full page-enter">
      <div className="sticky top-16 z-20 bg-card/75 backdrop-blur-md border-b border-border/80 px-6 py-3 flex items-center gap-3 no-print">
        <Link
          href="/audits"
          className="flex items-center gap-1.5 text-sm text-on-surface-variant hover:text-on-surface transition-colors"
        >
          <ChevronLeft className="h-4 w-4" />
          {t("backToAudits")}
        </Link>
        <div className="w-px h-4 bg-border mx-1" />
        <span className="text-xs font-mono text-on-surface-variant">{audit.id}</span>
        <span className="text-xs text-on-surface-variant">·</span>
        <span className="text-xs text-on-surface-variant truncate max-w-[200px]">
          {audit.workflowName}
        </span>
        <div className="flex-1" />
        <Button variant="outline" size="sm" className="gap-1.5" onClick={() => window.print()}>
          <Printer className="h-3.5 w-3.5" />
          {t("exportPdf")}
        </Button>
        <Button asChild variant="outline" size="sm" className="gap-1.5">
          <a href={`/api/v1/audits/${encodeURIComponent(audit.id)}/export.csv`} download>
            <Download className="h-3.5 w-3.5" />
            {t("exportCsv")}
          </a>
        </Button>
      </div>

      <div className="hidden print:flex items-center justify-between mb-6 pb-4 border-b">
        <div>
          <h1 className="text-2xl font-bold">{t("printTitle")}</h1>
          <p className="text-sm text-slate-700">
            {audit.id} · {audit.workflowName}
          </p>
        </div>
        <div className="text-right text-sm text-slate-600">
          <p>{t("generatedOn")}</p>
          <p>
            <DateTime value={now} />
          </p>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-6 py-8 space-y-8 page-enter-stagger">
        <div className="flex items-center gap-2 text-sm text-on-surface-variant">
          <span>
            {t("runOn")} {ranAt}
          </span>
          <span>·</span>
          <span className="capitalize">
            {t("via")} {via}
          </span>
        </div>

        <RunStatusBanner
          audit={audit}
          subtitle={
            <>
              {audit.workflowName} · {ranAt}
            </>
          }
          className="rounded-2xl p-6 print:rounded-none [&_p:first-child]:text-xl"
          footer={
            <>
              <span className="text-xs bg-surface-container px-3 py-1 rounded-full text-on-surface-variant">
                {t("source")}: {audit.workflowName}
              </span>
              <span className="text-xs bg-surface-container px-3 py-1 rounded-full text-on-surface-variant capitalize">
                {t("via")} {via}
              </span>
            </>
          }
        />

        <section className="space-y-3">
          <h2 className="font-display text-lg font-semibold text-on-surface">{t("runDetails")}</h2>
          <RunMetadataPanel metadata={audit.metadata} />
        </section>

        <section className="space-y-4 print:break-before-page">
          <div className="flex items-center gap-2.5">
            <FileText className="h-5 w-5 text-on-surface-variant" />
            <h2 className="font-display text-lg font-semibold text-on-surface">
              {t("extractedData")}
            </h2>
          </div>
          {audit.documents.map((doc) => (
            <ReportDocument key={doc.id} doc={doc} />
          ))}
        </section>

        <section className="space-y-4">
          <div className="flex items-center gap-2.5">
            <ShieldCheck className="h-5 w-5 text-on-surface-variant" />
            <h2 className="font-display text-lg font-semibold text-on-surface">
              {t("validationRules")}
            </h2>
          </div>
          {byRuleStatus(audit.ruleResults).map((rule) => (
            <RunDetailedRuleCard key={rule.id} rule={rule} size="md" />
          ))}
        </section>
      </div>
    </div>
  );
}
