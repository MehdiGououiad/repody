"use client";

import { ChevronRight } from "lucide-react";
import { useFormatter, useLocale, useTranslations } from "next-intl";
import { DateTime } from "@/components/shared/date-time";
import { Badge } from "@/components/ui/badge";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { StatusGlyph } from "@/components/ui/status-glyph";
import { DocumentExtractionOutput } from "@/components/workflow/extraction-output-panel";
import type { RunAuditDetail, RunAuditDocument, RunAuditRule } from "@/lib/types";
import { cn, formatDurationMs, formatExtractedFieldValue } from "@/lib/utils";

const VERDICT = {
  passed: { glyph: "passed", key: "allRulesPassed" },
  warning: { glyph: "warning", key: "reviewRequired" },
  failed: { glyph: "failed", key: "validationFailed" },
} as const;

/** The verdict: one line that says what happened, one line of facts under it. */
export function ReportVerdict({ audit, className }: { audit: RunAuditDetail; className?: string }) {
  const t = useTranslations("audits.report");
  const { glyph, key } = VERDICT[audit.status];
  const { summary, metadata } = audit;
  const facts = [
    summary.total ? t("rulesPassed", { passed: summary.passed, total: summary.total }) : null,
    t("fieldsExtracted", { count: summary.fieldsExtracted }),
    metadata?.durationMs != null ? formatDurationMs(metadata.durationMs) : null,
    audit.source === "api" ? t("viaApi") : t("viaTest"),
  ].filter(Boolean);
  return (
    <div className={cn("flex items-start gap-3", className)}>
      <StatusGlyph status={glyph} className="mt-1 size-5" />
      <div className="min-w-0">
        <p className="text-xl font-semibold text-ink">{t(key)}</p>
        <p className="mt-1 text-sm text-ink-3">
          {facts.join(" · ")} ·{" "}
          <DateTime value={audit.createdAt} format={{ dateStyle: "medium", timeStyle: "short" }} />
        </p>
      </div>
    </div>
  );
}

/** Fields as ledger lines: the margin mark, the field, the value; flagged lines say which rule. */
function DocumentLedger({ doc, rules }: { doc: RunAuditDocument; rules: RunAuditRule[] }) {
  const t = useTranslations("audits.report");
  const locale = useLocale();
  const error = doc.extraction?.error;
  const failedBy = (key: string) =>
    rules.filter((r) => r.status === "failed" && r.affectedFields.includes(key)).map((r) => r.name);

  return (
    <section className="overflow-hidden rounded-lg shadow-[0_0_0_1px_var(--line)] print-keep">
      <header className="flex h-10 items-center gap-2 border-b border-line bg-raised px-4">
        <span className="truncate text-sm font-medium text-ink">{doc.documentType}</span>
        {doc.fileName ? <span className="truncate text-xs text-ink-3">{doc.fileName}</span> : null}
        <span className="ms-auto shrink-0 text-xs tabular-nums text-ink-3">
          {t("docExtracted", {
            done: doc.fields.filter((f) => f.extracted).length,
            total: doc.fields.length,
          })}
        </span>
      </header>
      {error ? (
        <p
          role="alert"
          className="flex items-start gap-2 border-b border-line px-4 py-3 text-sm text-fail-ink"
        >
          <StatusGlyph status="failed" className="mt-0.5" />
          <span>
            <span className="font-medium">{t("extractionFailed")}.</span> {error}
          </span>
        </p>
      ) : null}
      {doc.extraction && !error && doc.extraction.pagesSent < doc.extraction.pagesRendered ? (
        <p className="border-b border-line px-4 py-2 text-xs text-warn-ink">
          {t("pagesTruncated", {
            sent: doc.extraction.pagesSent,
            total: doc.extraction.pagesRendered,
          })}
        </p>
      ) : null}
      <ul className="divide-y divide-line">
        {doc.fields.map((field) => {
          const notes = field.flagged ? failedBy(field.key) : [];
          return (
            <li
              key={field.key}
              className={cn(
                "grid grid-cols-[14px_minmax(0,2fr)_minmax(0,3fr)] items-baseline gap-3 px-4 py-2.5",
                field.flagged && "bg-fail-wash/50"
              )}
            >
              <StatusGlyph
                status={!field.extracted ? "waiting" : field.flagged ? "failed" : "passed"}
                label={!field.extracted ? t("notFound") : field.flagged ? t("failed") : t("passed")}
                className="translate-y-0.5"
              />
              <span className="min-w-0">
                <span className="block truncate font-mono text-xs text-ink-2">{field.key}</span>
                {field.description ? (
                  <span className="block truncate text-xs text-ink-4">{field.description}</span>
                ) : null}
              </span>
              <span className="min-w-0">
                <span
                  className={cn(
                    "block break-words text-sm tabular-nums",
                    field.extracted ? "font-medium text-ink" : "text-ink-4"
                  )}
                >
                  {field.extracted ? formatExtractedFieldValue(field.value, locale) : t("notFound")}
                </span>
                {notes.length ? (
                  <span className="mt-0.5 block text-xs text-fail-ink">{notes.join(", ")}</span>
                ) : null}
              </span>
            </li>
          );
        })}
      </ul>
      {doc.extraction && !error && (doc.extraction.rawText || doc.extraction.markdownText) ? (
        <Collapsible className="border-t border-line">
          <CollapsibleTrigger className="group flex h-9 w-full cursor-pointer items-center gap-1.5 px-4 text-xs text-ink-3 transition-colors duration-100 hover:text-ink">
            <ChevronRight
              className="size-3.5 transition-transform duration-150 group-data-[state=open]:rotate-90"
              aria-hidden
            />
            {t("modelOutput")}
            <span className="ms-auto tabular-nums">
              {formatDurationMs(doc.extraction.extractionMs)}
            </span>
          </CollapsibleTrigger>
          <CollapsibleContent className="px-4 pb-4">
            <DocumentExtractionOutput extraction={doc.extraction} />
          </CollapsibleContent>
        </Collapsible>
      ) : null}
    </section>
  );
}

const RULE_ORDER = { failed: 0, skipped: 1, passed: 2 } as const;

/** Rules, failures first; a failed rule says why and which fields it read. */
function RuleList({ rules }: { rules: RunAuditRule[] }) {
  const t = useTranslations("audits.report");
  const sorted = [...rules].sort((a, b) => RULE_ORDER[a.status] - RULE_ORDER[b.status]);
  return (
    <ul className="divide-y divide-line overflow-hidden rounded-lg shadow-[0_0_0_1px_var(--line)]">
      {sorted.map((rule) => {
        const failed = rule.status === "failed";
        return (
          <li
            key={rule.id}
            className="grid grid-cols-[14px_minmax(0,1fr)] gap-x-3 gap-y-1 px-4 py-3 print-keep"
          >
            <StatusGlyph
              status={failed ? (rule.severity === "flag" ? "warning" : "failed") : rule.status}
              label={t(rule.status)}
              className="translate-y-0.5"
            />
            <div className="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1">
              <span className="text-sm font-medium text-ink">{rule.name}</span>
              {failed ? (
                <Badge variant={rule.severity === "flag" ? "warning" : "danger"}>
                  {t(rule.severity === "reject" ? "reject" : "flag")}
                </Badge>
              ) : null}
              <span className="text-xs text-ink-4">
                {t(rule.scope === "cross" ? "cross" : "intra")}
              </span>
            </div>
            <code className="col-start-2 block break-words font-mono text-xs text-ink-3">
              {rule.expression}
            </code>
            {failed && rule.detail ? (
              <p className="col-start-2 text-sm text-ink-2">{rule.detail}</p>
            ) : null}
          </li>
        );
      })}
    </ul>
  );
}

/** The body of a report: documents and their fields, then the rules. */
export function ReportBody({
  audit,
  compact = false,
}: {
  audit: RunAuditDetail;
  compact?: boolean;
}) {
  const t = useTranslations("audits.report");
  const format = useFormatter();
  return (
    <div
      className={cn(
        "grid grid-cols-1 gap-8",
        !compact && "xl:grid-cols-[minmax(0,3fr)_minmax(0,2fr)] xl:items-start"
      )}
    >
      <div className="flex flex-col gap-3">
        <h2 className="text-sm font-semibold text-ink">{t("extractedData")}</h2>
        {audit.documents.map((doc) => (
          <DocumentLedger key={doc.id} doc={doc} rules={audit.ruleResults} />
        ))}
      </div>
      {audit.ruleResults.length ? (
        <div className={cn("flex flex-col gap-3", !compact && "xl:sticky xl:top-16")}>
          <h2 className="flex items-baseline justify-between text-sm font-semibold text-ink">
            {t("validationRules")}
            <span className="text-xs font-normal tabular-nums text-ink-3">
              {t("rulesPassed", {
                passed: format.number(audit.summary.passed),
                total: format.number(audit.summary.total),
              })}
            </span>
          </h2>
          <RuleList rules={audit.ruleResults} />
        </div>
      ) : null}
    </div>
  );
}
