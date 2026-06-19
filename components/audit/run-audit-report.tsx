"use client";

import { useTranslations, useLocale } from "next-intl";
import Link from "next/link";
import {
  ChevronLeft, Download, FileText, ShieldCheck,
  CheckCircle2, AlertTriangle,
  Globe, Printer,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { LOCALE_COOKIE } from "@/i18n/config";
import { ruleStatusLabel, isRuleFailure } from "@/lib/rule-status";
import type { RunAuditDetail } from "@/lib/types/audit";
import { formatDurationMs } from "@/lib/types/audit";
import {
  ConfidenceBar,
  RunDetailedRuleCard,
  RunStatusBanner,
  formatFieldValue,
  type RunReportLabels,
} from "@/components/audit/run-report/run-report-core";
import { DocumentExtractionMeta, RunMetadataPanel } from "@/components/workflow/run-details-meta";
import { DocumentExtractionOutput } from "@/components/workflow/extraction-output-panel";

// ── CSV export ────────────────────────────────────────────────────────────────

function buildCsv(audit: RunAuditDetail, t: ReturnType<typeof useTranslations>, locale: string): string {
  const esc = (v: string) => `"${v.replace(/"/g, '""')}"`;
  const rows: string[] = [];

  rows.push(`${t("printTitle")} — ${audit.id}`);
  rows.push(`${t("runOn")}: ${new Date(audit.createdAt).toLocaleString(locale)}`);
  rows.push(`${t("source")}: ${audit.workflowName}`);
  if (audit.metadata) {
    rows.push(`${t("runDetails")}: ${audit.metadata.validationLabel}`);
    rows.push(`${t("totalDuration")}: ${formatDurationMs(audit.metadata.durationMs)}`);
    rows.push(`${t("extractionTime")}: ${formatDurationMs(audit.metadata.extractionMs)}`);
    rows.push(`${t("validationTime")}: ${formatDurationMs(audit.metadata.validationMs)}`);
  }
  rows.push("");

  rows.push(t("extractedData"));
  rows.push([t("field"), t("value"), "Type", t("confidence"), t("status")].map(esc).join(","));
  for (const doc of audit.documents) {
    rows.push(`--- ${doc.documentType} ---`);
    if (doc.extraction) {
      rows.push(
        [
          "Engine",
          doc.extraction.readPathLabel,
          "Validation",
          doc.extraction.validationLabel,
          "Ms",
          String(doc.extraction.extractionMs),
        ].map(esc).join(",")
      );
    }
    for (const f of doc.fields) {
      rows.push([
        f.key,
        formatFieldValue(f, locale),
        f.type,
        f.confidence !== null ? `${Math.round(f.confidence * 100)}%` : "",
        f.flagged ? t("failed") : t("passed"),
      ].map(esc).join(","));
    }
  }
  rows.push("");

  rows.push(t("validationRules"));
  rows.push(["ID", t("field"), "Kind", "Scope", t("status"), t("source")].map(esc).join(","));
  for (const r of audit.ruleResults) {
    rows.push([r.name, r.expression, r.kind, r.scope, ruleStatusLabel(r.status), r.detail].map(esc).join(","));
  }

  return rows.join("\r\n");
}

function downloadCsv(content: string, filename: string) {
  const blob = new Blob(["﻿" + content], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function auditReportLabels(t: ReturnType<typeof useTranslations>, audit: RunAuditDetail): RunReportLabels {
  return {
    allPassed: t("allRulesPassed"),
    validationFailed: t("validationFailed"),
    reviewRequired: t("reviewRequired"),
    fieldsExtracted: t("fieldsExtracted", { count: audit.summary.fieldsExtracted })
      .replace(String(audit.summary.fieldsExtracted), "")
      .trim(),
    rulesPassed: t("rulesPassed", { passed: audit.summary.passed, total: audit.summary.total }),
    rulesFailed: t("rulesFailed", { count: audit.summary.failed }),
    expected: t("expected"),
    got: t("got"),
    logic: t("logic"),
    llm: t("llm"),
    cross: t("cross"),
    intra: t("intra"),
    reject: t("reject"),
    flag: t("flag"),
    info: t("info"),
    passed: t("passed"),
    affectedFields: t("affectedFields"),
    extractedData: t("extractedData"),
    validationResults: t("validationRules"),
  };
}

// ── Language switcher ─────────────────────────────────────────────────────────

function LangToggle() {
  const locale = useLocale();
  const t = useTranslations("audits.report");
  const toggle = () => {
    const next = locale === "fr" ? "en" : "fr";
    document.cookie = `${LOCALE_COOKIE}=${next}; path=/; max-age=${60 * 60 * 24 * 365}; samesite=lax`;
    window.location.reload();
  };
  return (
    <button
      type="button"
      onClick={toggle}
      aria-label={t("toggleLanguage")}
      className="inline-flex items-center gap-1.5 text-xs font-medium text-on-surface-variant hover:text-on-surface border border-border rounded-lg px-3 py-1.5 transition-colors"
    >
      <Globe className="h-3.5 w-3.5" aria-hidden="true" />
      {locale === "fr" ? "EN" : "FR"}
    </button>
  );
}

// ── Extraction table ──────────────────────────────────────────────────────────

function DocExtractionCard({
  doc,
  t,
  locale,
}: {
  doc: RunAuditDetail["documents"][number];
  t: ReturnType<typeof useTranslations>;
  locale: string;
}) {
  return (
    <div className="rounded-xl border border-border bg-card overflow-hidden panel-elevated">
      <div className="flex items-center gap-3 px-5 py-3 border-b border-border bg-surface-container-low">
        <FileText className="h-4 w-4 text-primary shrink-0" />
        <div className="min-w-0 flex-1">
          <span className="text-sm font-semibold text-on-surface">{doc.documentType}</span>
          {doc.fileName && (
            <p className="text-[11px] text-on-surface-variant truncate">{doc.fileName}</p>
          )}
        </div>
        <span className="ml-auto text-[11px] text-on-surface-variant shrink-0">
          {doc.fields.filter((f) => f.extracted).length} / {doc.fields.length}{" "}
          {t("fieldsExtracted", { count: 0 }).replace("0", "").trim()}
        </span>
      </div>
      {doc.extraction && (
        <div className="px-5 py-3 border-b border-border bg-surface-container-lowest space-y-3">
          <DocumentExtractionMeta extraction={doc.extraction} fileName={doc.fileName} />
          <DocumentExtractionOutput extraction={doc.extraction} />
        </div>
      )}

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border bg-surface-container-lowest">
              <th className="text-left px-5 py-2.5 text-[11px] font-semibold uppercase tracking-wide text-on-surface-variant w-[30%]">{t("field")}</th>
              <th className="text-left px-4 py-2.5 text-[11px] font-semibold uppercase tracking-wide text-on-surface-variant">{t("value")}</th>
              <th className="text-left px-4 py-2.5 text-[11px] font-semibold uppercase tracking-wide text-on-surface-variant w-[160px]">{t("confidence")}</th>
              <th className="text-right px-5 py-2.5 text-[11px] font-semibold uppercase tracking-wide text-on-surface-variant w-[80px]">{t("status")}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {doc.fields.map((field) => (
              <tr
                key={field.key}
                className={cn(
                  "transition-colors",
                  field.flagged
                    ? "bg-danger/4 border-l-2 border-l-danger"
                    : "hover:bg-surface-container-lowest"
                )}
              >
                <td className="px-5 py-3">
                  <code className={cn("text-[12px] font-mono", field.flagged ? "text-danger" : "text-primary")}>
                    {field.key}
                  </code>
                  {field.description && (
                    <p className="text-[10px] text-on-surface-variant mt-0.5 max-w-[220px] truncate">{field.description}</p>
                  )}
                </td>
                <td className="px-4 py-3">
                  <span className={cn("font-semibold", !field.extracted ? "text-on-surface-variant" : field.flagged ? "text-danger" : "text-on-surface")}>
                    {formatFieldValue(field, locale)}
                  </span>
                </td>
                <td className="px-4 py-3">
                  {field.confidence !== null && field.extracted ? (
                    <ConfidenceBar value={field.confidence} />
                  ) : (
                    <span className="text-[11px] text-on-surface-variant">—</span>
                  )}
                </td>
                <td className="px-5 py-3 text-right">
                  {field.flagged ? (
                    <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-danger">
                      <AlertTriangle className="h-3 w-3" />
                    </span>
                  ) : (
                    <CheckCircle2 className="h-4 w-4 text-success ml-auto" />
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ── Main export ───────────────────────────────────────────────────────────────

export function RunAuditReport({ audit }: { audit: RunAuditDetail }) {
  const t = useTranslations("audits.report");
  const locale = useLocale();
  const labels = auditReportLabels(t, audit);
  const generatedAt = new Date().toLocaleString(locale);

  const handlePrint = () => window.print();

  const handleCsv = () => {
    const csv = buildCsv(audit, t, locale);
    const ts = new Date(audit.createdAt).toISOString().slice(0, 10);
    downloadCsv(csv, `audit-${audit.id}-${ts}.csv`);
  };

  const failed = audit.ruleResults.filter((r) => isRuleFailure(r.status));
  const passed = audit.ruleResults.filter((r) => r.status === "passed");
  const other = audit.ruleResults.filter(
    (r) => r.status !== "passed" && !isRuleFailure(r.status)
  );

  const ts = new Date(audit.createdAt).toLocaleString(locale, {
    year: "numeric", month: "long", day: "numeric",
    hour: "2-digit", minute: "2-digit",
  });

  return (
    <div className="min-h-full page-enter">
      <div className="sticky top-16 z-20 bg-card/75 backdrop-blur-md border-b border-border/80 px-6 py-3 flex items-center gap-3 no-print">
        <Link href="/audits" className="flex items-center gap-1.5 text-sm text-on-surface-variant hover:text-on-surface transition-colors">
          <ChevronLeft className="h-4 w-4" />
          {t("backToAudits")}
        </Link>
        <div className="w-px h-4 bg-border mx-1" />
        <span className="text-xs font-mono text-on-surface-variant">{audit.id}</span>
        <span className="text-xs text-on-surface-variant">·</span>
        <span className="text-xs text-on-surface-variant truncate max-w-[200px]">{audit.workflowName}</span>
        <div className="flex-1" />
        <LangToggle />
        <Button variant="outline" size="sm" className="gap-1.5" onClick={handlePrint}>
          <Printer className="h-3.5 w-3.5" />
          {t("exportPdf")}
        </Button>
        <Button variant="outline" size="sm" className="gap-1.5" onClick={handleCsv}>
          <Download className="h-3.5 w-3.5" />
          {t("exportCsv")}
        </Button>
      </div>

      <div className="hidden print:flex items-center justify-between mb-6 pb-4 border-b">
        <div>
          <h1 className="text-2xl font-bold">{t("printTitle")}</h1>
          <p className="text-sm text-slate-600 print:text-slate-700">{audit.id} · {audit.workflowName}</p>
        </div>
        <div className="text-right text-sm text-slate-500 print:text-slate-600">
          <p>{t("generatedOn")}</p>
          <p>{generatedAt}</p>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-6 py-8 space-y-8 page-enter-stagger">
        <div className="flex items-center gap-2 text-sm text-on-surface-variant">
          <span>{t("runOn")} {ts}</span>
          <span>·</span>
          <span className="capitalize">{t("via")} {audit.source === "api" ? t("api") : t("interface")}</span>
        </div>

        <RunStatusBanner
          audit={audit}
          labels={labels}
          subtitle={`${audit.workflowName} · ${ts}`}
          className="rounded-2xl p-6 print:rounded-none [&_p:first-child]:text-xl"
          footer={
            <>
              <span className="text-xs bg-surface-container px-3 py-1 rounded-full text-on-surface-variant">
                {t("source")}: {audit.workflowName}
              </span>
              <span className="text-xs bg-surface-container px-3 py-1 rounded-full text-on-surface-variant capitalize">
                {t("via")} {audit.source === "api" ? t("api") : t("interface")}
              </span>
            </>
          }
        />

        {audit.metadata && (
          <section className="space-y-3">
            <h2 className="font-display text-lg font-semibold text-on-surface">{t("runDetails")}</h2>
            <RunMetadataPanel metadata={audit.metadata} />
          </section>
        )}

        <section className="space-y-4 print:break-before-page">
          <div className="flex items-center gap-2.5">
            <FileText className="h-5 w-5 text-on-surface-variant" />
            <h2 className="font-display text-lg font-semibold text-on-surface">{t("extractedData")}</h2>
          </div>
          {audit.documents.map((doc) => (
            <DocExtractionCard key={doc.id} doc={doc} t={t} locale={locale} />
          ))}
        </section>

        <section className="space-y-4">
          <div className="flex items-center gap-2.5">
            <ShieldCheck className="h-5 w-5 text-on-surface-variant" />
            <h2 className="font-display text-lg font-semibold text-on-surface">{t("validationRules")}</h2>
          </div>
          {[...failed, ...other, ...passed].map((rule) => (
            <RunDetailedRuleCard key={rule.id} rule={rule} labels={labels} size="md" />
          ))}
        </section>

        <div className="hidden print:block text-xs text-slate-500 print:text-slate-600 pt-4 border-t text-center">
          {audit.id} · {audit.workflowName} · {t("generatedOn")} {new Date().toLocaleString(locale)}
        </div>
      </div>
    </div>
  );
}
