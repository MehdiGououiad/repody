"use client";

import { useTranslations } from "next-intl";
import { StatusGlyph } from "@/components/ui/status-glyph";
import { TabsList, TabsTab } from "@/components/ui/tabs";
import type { DocumentDef, WorkflowRule } from "@/lib/types";

export type BuilderStep = 0 | 1 | 2;

const STEP_KEYS = ["fields", "rules", "testDeploy"] as const;

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

export function stepBlocked(
  step: BuilderStep,
  documents: DocumentDef[],
  rules: WorkflowRule[]
): boolean {
  return (step === 1 || step === 2) && !stepComplete(0, documents, rules);
}

export const STEP_VALUES = STEP_KEYS;

export function BuilderTabs({
  documents,
  rules,
  done: published,
}: {
  documents: DocumentDef[];
  rules: WorkflowRule[];
  done: boolean;
}) {
  const t = useTranslations("workflows.builder.steps");
  return (
    <TabsList variant="segmented" aria-label={t("navTitle")}>
      {STEP_KEYS.map((key, i) => {
        const step = i as BuilderStep;
        const blocked = stepBlocked(step, documents, rules);
        const done = step === 2 ? published : stepComplete(step, documents, rules);
        return (
          <TabsTab
            key={key}
            value={key}
            disabled={blocked}
            title={blocked ? t("blockedHint") : undefined}
            className="h-6 px-2.5 text-xs data-disabled:cursor-not-allowed data-disabled:opacity-45"
          >
            <StatusGlyph status={done ? "passed" : "waiting"} className="size-3" />
            <span className="tabular-nums text-ink-4">{i + 1}</span>
            {t(key)}
          </TabsTab>
        );
      })}
    </TabsList>
  );
}
