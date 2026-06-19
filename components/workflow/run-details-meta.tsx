"use client";

import { useLocale, useTranslations } from "next-intl";
import { Brain, Clock, FileSearch, ShieldCheck, Snowflake, Sparkles } from "lucide-react";

import type { RunAuditDetail, RunAuditMetadata, RunDocumentExtractionMeta } from "@/lib/types/audit";
import { formatDurationMs } from "@/lib/types/audit";
import { DocumentExtractionOutput } from "@/components/workflow/extraction-output-panel";
import { publicDocumentModelLabel } from "@/lib/document-model-branding";
import { cn, formatExtractedFieldValue } from "@/lib/utils";

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
    <div className={cn("rounded-lg border border-border bg-surface-container-low px-3 py-2", className)}>
      <p className="text-[10px] font-semibold uppercase tracking-wide text-on-surface-variant">{label}</p>
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
  return (
    <div className={cn("grid grid-cols-2 sm:grid-cols-3 gap-2", className)}>
      <MetaChip label="Validation" value={metadata.validationLabel || metadata.validationMode} />
      <MetaChip label="Total duration" value={formatDurationMs(metadata.durationMs)} />
      <MetaChip label="Extraction" value={formatDurationMs(metadata.extractionMs)} />
      <MetaChip label="Validation time" value={formatDurationMs(metadata.validationMs)} />
      {metadata.llmModel && <MetaChip label="LLM model" value={metadata.llmModel} className="col-span-2 sm:col-span-1" />}
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
      <span className="inline-flex items-center gap-1 rounded-full bg-accent-blue/10 text-accent-blue px-2 py-0.5 font-medium">
        {extraction.readPathLabel}
        {extraction.readPathUsed !== extraction.readPathConfig && (
          <span className="opacity-70">(auto → {extraction.readPathUsed})</span>
        )}
      </span>
      <span className="inline-flex items-center gap-1 rounded-full bg-surface-container px-2 py-0.5">
        <ShieldCheck className="h-3 w-3" />
        {extraction.validationLabel}
      </span>
      {extraction.ocrModel && (
        <span className="rounded-full bg-surface-container px-2 py-0.5">
          Model: {publicDocumentModelLabel(extraction.ocrModel)}
        </span>
      )}
      {extraction.combinedLlm && (
        <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 text-primary px-2 py-0.5">
          <Brain className="h-3 w-3" />
          Combined extract + LLM
        </span>
      )}
      {extraction.cacheHit && (
        <span className="inline-flex items-center gap-1 rounded-full bg-success/10 text-success px-2 py-0.5">
          <Sparkles className="h-3 w-3" />
          Cached
        </span>
      )}
      {extraction.pagesDropped ? (
        <span className="inline-flex items-center gap-1 rounded-full bg-warning/10 text-warning px-2 py-0.5">
          {t("pagesTruncated", {
            sent: extraction.pagesSent ?? 0,
            total: extraction.pagesRendered ?? 0,
          })}
        </span>
      ) : null}
      {extraction.gpuColdStartLikely && (
        <span className="inline-flex items-center gap-1 rounded-full bg-sky-500/10 text-sky-700 dark:text-sky-300 px-2 py-0.5">
          <Snowflake className="h-3 w-3" />
          {t("gpuColdStartDone")}
        </span>
      )}
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
    (d) =>
      d.extraction &&
      ((d.extraction.markdownExtraction && d.extraction.ocrText) || d.extraction.rawText)
  );

  return (
    <div className="space-y-4">
      {result.metadata && <RunMetadataPanel metadata={result.metadata} />}
      {hasOutput && (
        <div className="space-y-3">
          {result.documents
            .filter(
              (d) =>
                d.extraction &&
                ((d.extraction.markdownExtraction && d.extraction.ocrText) ||
                  d.extraction.rawText)
            )
            .map((doc) => (
              <DocumentExtractionOutput key={doc.id} extraction={doc.extraction!} />
            ))}
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
                    <div key={field.key} className="flex items-baseline justify-between gap-3 text-xs">
                      <code className="font-mono text-primary shrink-0">{field.key}</code>
                      <span
                        className={cn(
                          "font-semibold text-right truncate",
                          field.flagged ? "text-danger" : "text-on-surface"
                        )}
                      >
                        {field.extracted
                          ? formatExtractedFieldValue(field.value, field.type, locale)
                          : "—"}
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
