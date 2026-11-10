"use client";

import { Clock, FileSearch, Sparkles } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { DocumentExtractionOutput } from "@/components/workflow/extraction-output-panel";
import type { RunAuditDetail, RunAuditMetadata, RunDocumentExtractionMeta } from "@/lib/types";
import { cn, formatDurationMs, formatExtractedFieldValue } from "@/lib/utils";

function MetaChip({
  label,
  value,
  className,
}: {
  label: string;
  value: string;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "rounded-lg border border-border bg-surface-container-low px-3 py-2",
        className
      )}
    >
      <p className="text-[10px] font-semibold uppercase tracking-wide text-on-surface-variant">
        {label}
      </p>
      <p className="text-xs font-medium text-on-surface mt-0.5">{value}</p>
    </div>
  );
}

export function RunMetadataPanel({
  metadata,
  className,
}: {
  metadata: RunAuditMetadata;
  className?: string;
}) {
  const t = useTranslations("audits.report");
  return (
    <div className={cn("grid grid-cols-2 sm:grid-cols-3 gap-2", className)}>
      <MetaChip label={t("totalDuration")} value={formatDurationMs(metadata.durationMs)} />
      <MetaChip label={t("extractionTime")} value={formatDurationMs(metadata.extractionMs)} />
      <MetaChip label={t("validationTime")} value={formatDurationMs(metadata.validationMs)} />
    </div>
  );
}

export function DocumentExtractionMeta({
  extraction,
  fileName,
}: {
  extraction: RunDocumentExtractionMeta;
  fileName?: string | null;
}) {
  const t = useTranslations("runProgress");

  return (
    <div className="flex flex-wrap gap-2 text-[11px] text-on-surface-variant">
      {fileName && (
        <span className="inline-flex items-center gap-1 rounded-full bg-surface-container px-2 py-0.5">
          <FileSearch className="h-3 w-3" />
          {fileName}
        </span>
      )}
      {extraction.cacheHit && (
        <span className="inline-flex items-center gap-1 rounded-full bg-success/10 text-success px-2 py-0.5">
          <Sparkles className="h-3 w-3" />
          Cached
        </span>
      )}
      {extraction.pagesSent < extraction.pagesRendered ? (
        <span className="inline-flex items-center gap-1 rounded-full bg-warning/10 text-warning px-2 py-0.5">
          {t("pagesTruncated", {
            sent: extraction.pagesSent,
            total: extraction.pagesRendered,
          })}
        </span>
      ) : null}
      <span className="inline-flex items-center gap-1 rounded-full bg-surface-container px-2 py-0.5 tabular-nums">
        <Clock className="h-3 w-3" />
        {formatDurationMs(extraction.extractionMs)} · {extraction.fieldsExtracted} field(s)
      </span>
    </div>
  );
}

export function TestRunSummaryDetails({ result }: { result: RunAuditDetail }) {
  const locale = useLocale();
  const hasOutput = result.documents.some(
    (d) => d.extraction && (d.extraction.markdownText || d.extraction.rawText)
  );

  return (
    <div className="space-y-4">
      {result.metadata && <RunMetadataPanel metadata={result.metadata} />}
      {hasOutput && (
        <div className="space-y-3">
          {result.documents.flatMap((doc) => {
            const extraction = doc.extraction;
            if (!extraction) return [];
            const hasOutput = extraction.markdownText || extraction.rawText;
            if (!hasOutput) return [];
            return [<DocumentExtractionOutput key={doc.id} extraction={extraction} />];
          })}
        </div>
      )}
      {result.documents.some((d) => d.fields.length > 0) && (
        <div className="rounded-xl panel-elevated overflow-hidden">
          <div className="px-4 py-2.5 bg-surface-container-low border-b border-border">
            <p className="text-[11px] font-semibold uppercase tracking-wider text-on-surface-variant">
              Extracted fields
            </p>
          </div>
          <div className="divide-y divide-border">
            {result.documents.map((doc) => (
              <div key={doc.id} className="px-4 py-3 space-y-2">
                <p className="text-xs font-semibold text-on-surface">{doc.documentType}</p>
                {doc.extraction && (
                  <DocumentExtractionMeta extraction={doc.extraction} fileName={doc.fileName} />
                )}
                <div className="space-y-1.5">
                  {doc.fields.map((field) => (
                    <div
                      key={field.key}
                      className="flex items-baseline justify-between gap-3 text-xs"
                    >
                      <code className="font-mono text-primary shrink-0">{field.key}</code>
                      <span
                        className={cn(
                          "font-semibold text-right truncate",
                          field.flagged ? "text-danger" : "text-on-surface"
                        )}
                      >
                        {field.extracted ? formatExtractedFieldValue(field.value, locale) : "—"}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
