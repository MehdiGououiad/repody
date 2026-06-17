"use client";

import { AlertTriangle, FileText } from "lucide-react";
import { cn } from "@/lib/utils";
import type { RunAuditDetail, RunAuditDocument } from "@/lib/types/audit";
import {
  ConfidenceBar,
  formatFieldValue,
  mergeLabels,
  type RunReportLabels,
} from "./report-shared";

function RunDocFieldsCardHeader({
  doc,
  labels,
}: {
  doc: RunAuditDocument;
  labels?: RunReportLabels;
}) {
  const L = mergeLabels(labels);
  const extractedCount = doc.fields.filter((f) => f.extracted).length;
  const extractedLabel =
    typeof L.docExtracted === "function"
      ? L.docExtracted(extractedCount, doc.fields.length)
      : L.docExtracted ?? `${extractedCount}/${doc.fields.length} extracted`;

  return (
    <div className="flex items-center gap-2.5 px-4 py-3 border-b border-border bg-surface-container-low">
      <FileText className="h-4 w-4 text-primary shrink-0" aria-hidden="true" />
      <div className="min-w-0 flex-1">
        <span className="text-sm font-semibold text-on-surface">{doc.documentType}</span>
        {doc.fileName ? (
          <p className="text-[11px] text-on-surface-variant truncate">{doc.fileName}</p>
        ) : null}
      </div>
      <span className="ml-auto text-[10px] text-on-surface-variant shrink-0 tabular-nums">
        {extractedLabel}
      </span>
    </div>
  );
}

function RunDocFieldsListBody({
  doc,
  locale,
}: {
  doc: RunAuditDocument;
  locale: string;
}) {
  return (
    <div className="divide-y divide-border">
      {doc.fields.map((field) => (
        <div
          key={field.key}
          className={cn(
            "flex items-center gap-3 px-4 py-3 transition-colors",
            field.flagged ? "bg-danger/5 border-l-2 border-l-danger" : "hover:bg-surface-container-lowest"
          )}
        >
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <code
                className={cn(
                  "text-[11px] font-mono truncate",
                  field.flagged ? "text-danger" : "text-primary"
                )}
              >
                {field.key}
              </code>
              {field.flagged ? <AlertTriangle className="h-3 w-3 text-danger shrink-0" aria-hidden="true" /> : null}
            </div>
            {field.description ? (
              <p className="text-[10px] text-on-surface-variant truncate mt-0.5">
                {field.description}
              </p>
            ) : null}
          </div>
          <div className="text-right shrink-0">
            <p
              className={cn(
                "text-sm font-semibold tabular-nums",
                !field.extracted
                  ? "text-on-surface-variant"
                  : field.flagged
                    ? "text-danger"
                    : "text-on-surface"
              )}
            >
              {formatFieldValue(field, locale)}
            </p>
            {field.confidence !== null && field.extracted ? (
              <div className="flex justify-end mt-1">
                <ConfidenceBar value={field.confidence} />
              </div>
            ) : null}
          </div>
        </div>
      ))}
    </div>
  );
}

function RunDocFieldsTableBody({
  doc,
  locale,
}: {
  doc: RunAuditDocument;
  locale: string;
}) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-xs text-on-surface-variant border-b border-border">
            <th className="px-4 py-2">Field</th>
            <th className="px-4 py-2">Value</th>
            <th className="px-4 py-2">Confidence</th>
          </tr>
        </thead>
        <tbody>
          {doc.fields.map((field) => (
            <tr key={field.key} className="border-b border-border/50 last:border-0">
              <td className="px-4 py-2 font-mono text-xs">{field.key}</td>
              <td className="px-4 py-2 tabular-nums">{formatFieldValue(field, locale)}</td>
              <td className="px-4 py-2">
                {field.confidence != null ? (
                  <ConfidenceBar value={field.confidence} />
                ) : (
                  "—"
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** Compact list layout for builder panels and side previews. */
export function RunDocFieldsList({
  doc,
  locale,
  labels,
}: {
  doc: RunAuditDocument;
  locale: string;
  labels?: RunReportLabels;
}) {
  return (
    <div className="panel-elevated rounded-xl overflow-hidden">
      <RunDocFieldsCardHeader doc={doc} labels={labels} />
      <RunDocFieldsListBody doc={doc} locale={locale} />
    </div>
  );
}

/** Full table layout for printable audit reports. */
export function RunDocFieldsTable({
  doc,
  locale,
  labels,
}: {
  doc: RunAuditDocument;
  locale: string;
  labels?: RunReportLabels;
}) {
  return (
    <div className="panel-elevated rounded-xl overflow-hidden">
      <RunDocFieldsCardHeader doc={doc} labels={labels} />
      <RunDocFieldsTableBody doc={doc} locale={locale} />
    </div>
  );
}

export function RunFieldsList({
  audit,
  locale,
  labels,
}: {
  audit: RunAuditDetail;
  locale: string;
  labels?: RunReportLabels;
}) {
  return (
    <div className="space-y-4">
      {audit.documents.map((doc) => (
        <RunDocFieldsList key={doc.id} doc={doc} locale={locale} labels={labels} />
      ))}
    </div>
  );
}
