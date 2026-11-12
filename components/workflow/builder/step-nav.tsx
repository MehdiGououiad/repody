"use client";

import { useTranslations } from "next-intl";
import { StatusGlyph } from "@/components/ui/status-glyph";
import type { DocumentDef, WorkflowRule } from "@/lib/types";

export type BuilderStep = 0 | 1 | 2;

export const STEP_KEYS = ["extract", "rules", "upload"] as const;

export function stepComplete(
  step: BuilderStep,
  documents: DocumentDef[],
  rules: WorkflowRule[]
): boolean {
  if (step === 0)
    return documents.some((d) => d.documentType.trim() && d.schema.some((f) => f.name.trim()));
  if (step === 1) return rules.some((r) => r.name.trim() && r.conditions.length > 0);
  return false;
}

/** Rules and testing wait until a document has a name and a field. */
export function stepBlocked(
  step: BuilderStep,
  documents: DocumentDef[],
  rules: WorkflowRule[]
): boolean {
  return (step === 1 || step === 2) && !stepComplete(0, documents, rules);
}

/** The builder's steps as tabs, each with its status glyph; a blocked step says why. */
export function BuilderTabs({
  current,
  documents,
  rules,
  tested,
  onChange,
}: {
  current: BuilderStep;
  documents: DocumentDef[];
  rules: WorkflowRule[];
  tested: boolean;
  onChange: (step: BuilderStep) => void;
}) {
  const t = useTranslations("workflows.builder.steps");
  return (
    <nav
      aria-label={t("navTitle")}
      className="flex h-10 shrink-0 items-center gap-0.5 overflow-x-auto border-b border-line bg-panel px-3 md:px-4"
    >
      {STEP_KEYS.map((key, i) => {
        const step = i as BuilderStep;
        const blocked = stepBlocked(step, documents, rules);
        const done = step === 2 ? tested : stepComplete(step, documents, rules);
        return (
          <button
            key={key}
            type="button"
            disabled={blocked}
            aria-current={current === step ? "step" : undefined}
            title={blocked ? t("blockedHint") : undefined}
            onClick={() => onChange(step)}
            className="flex h-7 shrink-0 cursor-pointer items-center gap-2 rounded-md px-2.5 text-sm font-medium text-ink-3 transition-colors duration-100 hover:bg-hover hover:text-ink disabled:cursor-not-allowed disabled:opacity-45 disabled:hover:bg-transparent aria-[current=step]:bg-selected aria-[current=step]:text-ink"
          >
            <StatusGlyph status={done ? "passed" : "waiting"} />
            {t(key)}
          </button>
        );
      })}
    </nav>
  );
}
