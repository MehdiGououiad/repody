"use client";

import { Collapsible, CollapsiblePanel, CollapsibleTrigger } from "@ui-sdk/react/collapsible";
import { ChevronRight } from "lucide-react";
import { motion } from "motion/react";
import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";
import { DateTime } from "@/components/shared/date-time";
import { DocChip } from "@/components/shared/doc-chip";
import { StatusGlyph } from "@/components/ui/status-glyph";
import { DocumentExtractionOutput } from "@/components/workflow/extraction-output-panel";
import { MAX_DIFFERENCES, readDifferences } from "@/lib/audits/second-read";
import { EASE_OUT } from "@/lib/motion";
import type { RunAuditDetail, RunAuditDocument, RunAuditRule } from "@/lib/types";
import { cn, formatDurationMs, formatExtractedFieldValue } from "@/lib/utils";

const VERDICT = {
  passed: { glyph: "passed", key: "allRulesPassed", tone: "text-pass-ink" },
  warning: { glyph: "warning", key: "reviewRequired", tone: "text-warn-ink" },
  failed: { glyph: "failed", key: "validationFailed", tone: "text-fail-ink" },
} as const;

/** The verdict: the outcome at hero size, then the facts on one line. */
export function ReportVerdict({ audit, className }: { audit: RunAuditDetail; className?: string }) {
  const t = useTranslations("audits.report");
  const { glyph, key, tone } = VERDICT[audit.status];
  const { summary, metadata } = audit;
  // Fields a second read did not confirm: why a run whose rules all passed needs review.
  const toCheck = audit.documents.reduce(
    (count, doc) => count + Object.keys(doc.extraction?.unconfirmed ?? {}).length,
    0
  );
  const facts = [
    toCheck ? t("fieldsToCheck", { count: toCheck }) : null,
    summary.total ? t("rulesPassed", { passed: summary.passed, total: summary.total }) : null,
    t("fieldsExtracted", { count: summary.fieldsExtracted }),
    metadata?.durationMs ? formatDurationMs(metadata.durationMs) : null,
    audit.source === "api" ? t("viaApi") : t("viaTest"),
  ].filter(Boolean);
  return (
    <div className={cn("flex items-start gap-3", className)}>
      <motion.span
        initial={{ scale: 0.6, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ type: "spring", duration: 0.35, bounce: 0 }}
        className="mt-1 flex"
      >
        <StatusGlyph status={glyph} className="size-5" />
      </motion.span>
      <div className="min-w-0">
        <p className={cn("text-[22px] font-semibold leading-tight tracking-[-0.02em]", tone)}>
          {t(key)}
        </p>
        <p className="mt-1 text-[13px] text-ink-3">
          {facts.join(" · ")} ·{" "}
          <DateTime value={audit.createdAt} format={{ dateStyle: "medium", timeStyle: "short" }} />
        </p>
      </div>
    </div>
  );
}

/** Where the time went: model and queue, extraction, rules, as one bar that grows in. */
export function TimingBar({ audit }: { audit: RunAuditDetail }) {
  const t = useTranslations("audits.report.timing");
  const total = audit.metadata?.durationMs ?? 0;
  if (!total) return null;
  const extraction = Math.min(audit.metadata.extractionMs, total);
  const rules = Math.min(audit.metadata.validationMs, total - extraction);
  const parts = [
    { key: "model", ms: Math.max(total - extraction - rules, 0), color: "bg-ink-4" },
    { key: "extraction", ms: extraction, color: "bg-accent" },
    { key: "rules", ms: rules, color: "bg-pass" },
  ] as const;
  return (
    <div className="flex flex-col gap-2">
      <div className="flex h-1.5 overflow-hidden rounded-full bg-selected">
        {parts.map((part, i) =>
          part.ms ? (
            <motion.span
              key={part.key}
              className={cn("h-full", part.color)}
              initial={{ width: 0 }}
              animate={{ width: `${(part.ms / total) * 100}%` }}
              transition={{ duration: 0.5, ease: EASE_OUT, delay: 0.1 + i * 0.08 }}
            />
          ) : null
        )}
      </div>
      <ul className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-ink-3">
        {parts.map((part) => (
          <li key={part.key} className="flex items-center gap-1.5">
            <span className={cn("size-1.5 rounded-full", part.color)} aria-hidden />
            {t(part.key)}
            <span className="tabular-nums text-ink-2">{formatDurationMs(part.ms)}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

const RULE_ORDER = { failed: 0, skipped: 1, passed: 2 } as const;

/** Rules, failures first; pointing at one lights up the fields it read. */
function RuleList({
  rules,
  onFocusRule,
}: {
  rules: RunAuditRule[];
  onFocusRule: (rule: RunAuditRule | null) => void;
}) {
  const t = useTranslations("audits.report");
  const sorted = [...rules].sort((a, b) => RULE_ORDER[a.status] - RULE_ORDER[b.status]);
  return (
    <ul className="divide-y divide-line overflow-hidden rounded-lg bg-panel shadow-panel">
      {sorted.map((rule) => {
        const failed = rule.status === "failed";
        const status = failed ? (rule.severity === "flag" ? "warning" : "failed") : rule.status;
        return (
          <li
            key={rule.id}
            onPointerEnter={() => onFocusRule(rule)}
            onPointerLeave={() => onFocusRule(null)}
            className={cn(
              "grid grid-cols-[14px_minmax(0,1fr)] gap-x-3 gap-y-1 px-3.5 py-2.5 transition-colors duration-100 hover:bg-hover print-keep",
              failed && (rule.severity === "flag" ? "bg-warn-wash/50" : "bg-fail-wash/50")
            )}
          >
            <StatusGlyph status={status} label={t(rule.status)} className="translate-y-0.5" />
            <div className="flex min-w-0 flex-wrap items-baseline gap-x-2 gap-y-0.5">
              <span className="text-[13px] font-medium text-ink">{rule.name}</span>
              <span className="text-xs text-ink-4">
                {t(rule.scope === "cross" ? "cross" : "intra")}
              </span>
              {failed ? (
                <span
                  className={cn(
                    "ms-auto text-xs font-medium",
                    rule.severity === "flag" ? "text-warn-ink" : "text-fail-ink"
                  )}
                >
                  {t(rule.severity === "reject" ? "reject" : "flag")}
                </span>
              ) : null}
            </div>
            <code className="col-start-2 block break-words font-mono text-xs text-ink-3">
              {rule.expression}
            </code>
            {failed && rule.detail ? (
              <p className="col-start-2 text-[13px] text-ink-2">{rule.detail}</p>
            ) : null}
          </li>
        );
      })}
    </ul>
  );
}

/** One document's fields as ledger lines; fields the pointed rule reads are outlined. */
function DocumentFields({
  doc,
  index,
  rules,
  focused,
}: {
  doc: RunAuditDocument;
  index: number;
  rules: RunAuditRule[];
  focused: Set<string>;
}) {
  const t = useTranslations("audits.report");
  const locale = useLocale();
  const error = doc.extraction?.error;
  const unconfirmed = doc.extraction?.unconfirmed ?? {};
  const failedBy = (key: string) =>
    rules.filter((r) => r.status === "failed" && r.affectedFields.includes(key)).map((r) => r.name);
  /** What the second read saw differently, briefly: the rows, columns or items of a table or
   * list that differ, not the whole second read. */
  const secondRead = (first: unknown, second: unknown) => {
    const differences = readDifferences(first, second);
    const said = differences.slice(0, MAX_DIFFERENCES).map((d) => {
      switch (d.kind) {
        case "cell":
          return t("diffCell", {
            row: d.row,
            column: d.column,
            value: formatExtractedFieldValue(d.value, locale),
          });
        case "item":
          return t("diffItem", { item: d.item, value: formatExtractedFieldValue(d.value, locale) });
        case "rows":
          return t("diffRows", { first: d.first, second: d.second });
        case "items":
          return t("diffItems", { first: d.first, second: d.second });
        default:
          return formatExtractedFieldValue(d.value, locale);
      }
    });
    if (differences.length > MAX_DIFFERENCES) {
      said.push(t("diffMore", { count: differences.length - MAX_DIFFERENCES }));
    }
    return t("unconfirmed", {
      value: said.join(t("diffJoin")) || formatExtractedFieldValue(second, locale),
    });
  };
  /** Why a field is flagged: the rules it failed, and a second read that saw it differently. */
  const notesFor = (key: string, value: unknown) => [
    ...failedBy(key),
    ...(key in unconfirmed ? [secondRead(value, unconfirmed[key])] : []),
  ];
  const found = doc.fields.filter((f) => f.extracted).length;

  return (
    <section className="overflow-hidden rounded-lg bg-panel shadow-panel print-keep">
      <header className="flex h-9 items-center gap-2 border-b border-line bg-raised px-3.5">
        <DocChip index={index} className="text-[13px] font-medium text-ink">
          {doc.documentType}
        </DocChip>
        {doc.fileName ? <span className="truncate text-xs text-ink-3">{doc.fileName}</span> : null}
        <span className="ms-auto flex shrink-0 items-center gap-2 text-xs tabular-nums text-ink-3">
          <span className="h-1 w-12 overflow-hidden rounded-full bg-selected">
            <span
              className="block h-full rounded-full bg-pass"
              style={{ width: `${doc.fields.length ? (found / doc.fields.length) * 100 : 0}%` }}
            />
          </span>
          {t("docExtracted", { done: found, total: doc.fields.length })}
        </span>
      </header>
      {error ? (
        <p
          role="alert"
          className="flex items-start gap-2 border-b border-line px-3.5 py-2.5 text-[13px] text-fail-ink"
        >
          <StatusGlyph status="failed" className="mt-0.5" />
          <span>
            <span className="font-medium">{t("extractionFailed")}.</span> {error}
          </span>
        </p>
      ) : null}
      {doc.extraction && !error && doc.extraction.secondRead === "failed" ? (
        <p className="border-b border-line px-3.5 py-2 text-xs text-warn-ink">
          {t("secondReadFailed")}
        </p>
      ) : null}
      {doc.extraction && !error && doc.extraction.pagesSent < doc.extraction.pagesRendered ? (
        <p className="border-b border-line px-3.5 py-2 text-xs text-warn-ink">
          {t("pagesTruncated", {
            sent: doc.extraction.pagesSent,
            total: doc.extraction.pagesRendered,
          })}
        </p>
      ) : null}
      <ul className="divide-y divide-line">
        {doc.fields.map((field) => {
          const notes = field.flagged ? notesFor(field.key, field.value) : [];
          // Flagged only because a second read disagreed: a value to check, not a failed rule.
          const toCheck = field.flagged && !failedBy(field.key).length && field.key in unconfirmed;
          const lit = focused.has(field.key) || focused.has(`${doc.documentType}.${field.key}`);
          return (
            <li
              key={field.key}
              data-lit={lit || undefined}
              className={cn(
                "grid grid-cols-[14px_minmax(0,2fr)_minmax(0,3fr)] items-baseline gap-3 px-3.5 py-2 transition-[background-color,box-shadow] duration-150",
                field.flagged && (toCheck ? "bg-warn-wash/40" : "bg-fail-wash/40"),
                "data-lit:bg-accent-wash data-lit:shadow-[inset_2px_0_0_var(--accent)]"
              )}
            >
              <StatusGlyph
                status={
                  !field.extracted
                    ? "waiting"
                    : toCheck
                      ? "warning"
                      : field.flagged
                        ? "failed"
                        : "passed"
                }
                label={
                  !field.extracted
                    ? t("notFound")
                    : toCheck
                      ? t("toCheck")
                      : field.flagged
                        ? t("failed")
                        : t("passed")
                }
                className="translate-y-0.5"
              />
              <span className="min-w-0">
                <span className="block truncate text-[13px] font-medium text-ink">{field.key}</span>
                {field.description ? (
                  <span className="block truncate text-xs text-ink-4">{field.description}</span>
                ) : null}
              </span>
              <span className="min-w-0">
                <span
                  className={cn(
                    "block break-words text-[13px] tabular-nums",
                    field.extracted ? "font-medium text-ink" : "text-ink-4"
                  )}
                >
                  {field.extracted ? formatExtractedFieldValue(field.value, locale) : t("notFound")}
                </span>
                {notes.length ? (
                  <span
                    className={cn(
                      "mt-0.5 block text-xs",
                      toCheck ? "text-warn-ink" : "text-fail-ink"
                    )}
                  >
                    {notes.join(", ")}
                  </span>
                ) : null}
              </span>
            </li>
          );
        })}
      </ul>
      {doc.extraction && !error && (doc.extraction.rawText || doc.extraction.markdownText) ? (
        <Collapsible className="border-t border-line">
          <CollapsibleTrigger className="group flex h-8 w-full cursor-pointer items-center gap-1.5 px-3.5 text-xs text-ink-3 transition-colors duration-100 hover:text-ink">
            <ChevronRight
              className="size-3.5 transition-transform duration-150 group-data-open:rotate-90"
              aria-hidden
            />
            {t("rawOutput")}
            <span className="ms-auto tabular-nums">
              {formatDurationMs(doc.extraction.extractionMs)}
            </span>
          </CollapsibleTrigger>
          <CollapsiblePanel className="px-3.5 pb-3.5">
            <DocumentExtractionOutput extraction={doc.extraction} />
          </CollapsiblePanel>
        </Collapsible>
      ) : null}
    </section>
  );
}

/** The body of a report: the rules first (what was decided), then each document's fields. */
export function ReportBody({ audit }: { audit: RunAuditDetail }) {
  const t = useTranslations("audits.report");
  const [focusedRule, setFocusedRule] = useState<RunAuditRule | null>(null);
  const focused = new Set(focusedRule?.affectedFields ?? []);
  return (
    <div className="flex flex-col gap-6">
      {audit.ruleResults.length ? (
        <section className="flex flex-col gap-2">
          <h2 className="flex items-baseline justify-between text-[13px] font-semibold text-ink">
            {t("validationRules")}
            <span className="text-xs font-normal tabular-nums text-ink-3">
              {t("rulesPassed", { passed: audit.summary.passed, total: audit.summary.total })}
            </span>
          </h2>
          <RuleList rules={audit.ruleResults} onFocusRule={setFocusedRule} />
        </section>
      ) : null}
      <section className="flex flex-col gap-2">
        <h2 className="text-[13px] font-semibold text-ink">{t("extractedData")}</h2>
        {audit.documents.map((doc, index) => (
          <DocumentFields
            key={doc.id}
            doc={doc}
            index={index}
            rules={audit.ruleResults}
            focused={focused}
          />
        ))}
      </section>
    </div>
  );
}
