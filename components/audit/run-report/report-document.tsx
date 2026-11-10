"use client";

import { AlertTriangle, CheckCircle2, FileText, XCircle } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { DocumentExtractionOutput } from "@/components/workflow/extraction-output-panel";
import { DocumentExtractionMeta } from "@/components/workflow/run-details-meta";
import type { RunAuditDocument } from "@/lib/types";
import { cn, formatExtractedFieldValue } from "@/lib/utils";

/** One document of a report: its extraction (or why it failed) and every extracted field. */
export function ReportDocument({ doc }: { doc: RunAuditDocument }) {
  const t = useTranslations("audits.report");
  const locale = useLocale();
  const error = doc.extraction?.error;

  return (
    <div className="rounded-xl border border-border bg-card overflow-hidden panel-elevated">
      <div className="flex items-center gap-3 px-5 py-3 border-b border-border bg-surface-container-low">
        <FileText className="h-4 w-4 text-primary shrink-0" />
        <div className="min-w-0 flex-1">
          <span className="text-sm font-semibold text-on-surface">{doc.documentType}</span>
          {doc.fileName ? (
            <p className="text-[11px] text-on-surface-variant truncate">{doc.fileName}</p>
          ) : null}
        </div>
        <span className="ml-auto text-[11px] text-on-surface-variant shrink-0 tabular-nums">
          {t("docExtracted", {
            done: doc.fields.filter((f) => f.extracted).length,
            total: doc.fields.length,
          })}
        </span>
      </div>

      {error ? (
        <div
          role="alert"
          className="flex items-start gap-2 px-5 py-3 border-b border-danger/30 bg-danger/5 text-sm text-danger"
        >
          <XCircle className="h-4 w-4 shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold">{t("extractionFailed")}</p>
            <p className="text-xs text-danger-strong mt-0.5">{error}</p>
          </div>
        </div>
      ) : null}

      {doc.extraction && !error ? (
        <div className="px-5 py-3 border-b border-border bg-surface-container-lowest space-y-3">
          <DocumentExtractionMeta extraction={doc.extraction} fileName={doc.fileName} />
          <DocumentExtractionOutput extraction={doc.extraction} />
        </div>
      ) : null}

      {doc.fields.length > 0 ? (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-surface-container-lowest text-[11px] font-semibold uppercase tracking-wide text-on-surface-variant">
                <th className="text-left px-5 py-2.5 w-[30%]">{t("field")}</th>
                <th className="text-left px-4 py-2.5">{t("value")}</th>
                <th className="text-right px-5 py-2.5 w-[80px]">{t("status")}</th>
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
                    <code
                      className={cn(
                        "text-[12px] font-mono",
                        field.flagged ? "text-danger" : "text-primary"
                      )}
                    >
                      {field.key}
                    </code>
                    {field.description ? (
                      <p className="text-[10px] text-on-surface-variant mt-0.5 max-w-[220px] truncate">
                        {field.description}
                      </p>
                    ) : null}
                  </td>
                  <td
                    className={cn(
                      "px-4 py-3 font-semibold",
                      !field.extracted
                        ? "text-on-surface-variant"
                        : field.flagged
                          ? "text-danger"
                          : "text-on-surface"
                    )}
                  >
                    {field.extracted ? formatExtractedFieldValue(field.value, locale) : "—"}
                  </td>
                  <td className="px-5 py-3 text-right">
                    {field.flagged ? (
                      <AlertTriangle
                        className="h-3.5 w-3.5 text-danger ml-auto"
                        aria-label={t("failed")}
                      />
                    ) : (
                      <CheckCircle2
                        className="h-4 w-4 text-success ml-auto"
                        aria-label={t("passed")}
                      />
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </div>
  );
}
