"use client";

import { Toolbar, ToolbarButton } from "@ui-sdk/react/toolbar";
import { Check } from "lucide-react";
import { useTranslations } from "next-intl";
import { Fragment } from "react";
import type { DocumentDef, WorkflowRule } from "@/lib/types";
import { cn } from "@/lib/utils";

export type BuilderStep = 0 | 1 | 2;

export const STEP_KEYS = ["fields", "rules", "testDeploy"] as const;

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

/**
 * The builder's steps: buttons with one tab stop, the current one marked `aria-current="step"`
 * and a blocked one `aria-disabled` (ui-sdk's Stepper pattern; not tabs).
 */
export function BuilderSteps({
  step,
  documents,
  rules,
  deployed,
  onStepChange,
}: {
  step: BuilderStep;
  documents: DocumentDef[];
  rules: WorkflowRule[];
  deployed: boolean;
  onStepChange: (step: BuilderStep) => void;
}) {
  const t = useTranslations("workflows.builder.steps");
  return (
    <Toolbar aria-label={t("navTitle")} className="flex items-center gap-1">
      {STEP_KEYS.map((key, i) => {
        const index = i as BuilderStep;
        const current = index === step;
        const blocked = stepBlocked(index, documents, rules);
        const done = !current && (index === 2 ? deployed : stepComplete(index, documents, rules));
        return (
          <Fragment key={key}>
            {i > 0 ? (
              <span
                aria-hidden
                className={cn("h-px w-6 shrink-0", index <= step ? "bg-accent" : "bg-line-strong")}
              />
            ) : null}
            <ToolbarButton
              aria-current={current ? "step" : undefined}
              disabled={blocked}
              title={blocked ? t("blockedHint") : undefined}
              onClick={() => onStepChange(index)}
              className={cn(
                "group flex h-8 cursor-pointer items-center gap-2 rounded-full px-2.5 text-[13px] font-medium outline-none transition-colors duration-150 focus-visible:shadow-[0_0_0_2px_var(--focus)] data-disabled:cursor-not-allowed data-disabled:opacity-45",
                current
                  ? "bg-accent-wash text-accent-ink"
                  : "text-ink-3 hover:bg-hover hover:text-ink"
              )}
            >
              <span
                className={cn(
                  "flex size-5 items-center justify-center rounded-full text-[11px] font-semibold tabular-nums",
                  current && "bg-accent text-on-accent",
                  done && "bg-pass text-white",
                  !current && !done && "shadow-[inset_0_0_0_1.5px_var(--line-strong)] text-ink-3"
                )}
              >
                {done ? <Check className="size-3" strokeWidth={3} aria-hidden /> : i + 1}
              </span>
              {t(key)}
            </ToolbarButton>
          </Fragment>
        );
      })}
    </Toolbar>
  );
}
