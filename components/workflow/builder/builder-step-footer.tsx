"use client";

import { ArrowLeft, ArrowRight } from "lucide-react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import {
  stepComplete,
  type BuilderStep,
} from "@/components/workflow/builder/step-nav";
import type { DocumentDef, WorkflowRule } from "@/lib/types";

const CONTINUE_LABEL_KEY: Record<0 | 1, "continueToRules" | "continueToTest"> = {
  0: "continueToRules",
  1: "continueToTest",
};

export function canAdvanceFromStep(
  step: BuilderStep,
  documents: DocumentDef[],
  rules: WorkflowRule[]
): boolean {
  if (step === 0) return stepComplete(0, documents, rules);
  if (step === 1) return stepComplete(0, documents, rules);
  return false;
}

function continueHint(
  step: BuilderStep,
  documents: DocumentDef[],
  rules: WorkflowRule[],
  tSteps: ReturnType<typeof useTranslations>
): string | null {
  if (step === 0 && !stepComplete(0, documents, rules)) {
    return tSteps("continueBlockedSchema");
  }
  if (step === 1 && !stepComplete(1, documents, rules)) {
    return tSteps("continueRulesOptional");
  }
  return null;
}

export function BuilderStepFooter({
  step,
  documents,
  rules,
  onBack,
  onContinue,
}: {
  step: BuilderStep;
  documents: DocumentDef[];
  rules: WorkflowRule[];
  onBack: () => void;
  onContinue: () => void;
}) {
  const tSteps = useTranslations("workflows.builder.steps");

  if (step === 2) {
    return (
      <div className="shrink-0 border-t border-border/80 bg-card/95 backdrop-blur-sm px-5 py-3 md:px-6">
        <div className="mx-auto flex max-w-4xl items-center justify-between gap-3">
          <Button
            type="button"
            variant="ghost"
            size="sm"
            className="gap-1.5 h-9"
            onClick={onBack}
          >
            <ArrowLeft className="h-4 w-4" />
            {tSteps("back")}
          </Button>
          <p className="text-xs text-on-surface-variant text-center flex-1 hidden sm:block">
            {tSteps("finalStepHint")}
          </p>
        </div>
      </div>
    );
  }

  const canContinue = canAdvanceFromStep(step, documents, rules);
  const hint = continueHint(step, documents, rules, tSteps);

  return (
    <div className="shrink-0 border-t border-border/80 bg-card/95 backdrop-blur-sm px-5 py-3 md:px-6">
      <div className="mx-auto flex max-w-4xl flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3 min-w-0">
          {step > 0 ? (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="gap-1.5 h-9 shrink-0"
              onClick={onBack}
            >
              <ArrowLeft className="h-4 w-4" />
              {tSteps("back")}
            </Button>
          ) : null}
          <div className="min-w-0">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-on-surface-variant mb-0.5">
              {tSteps("stepOf", { current: step + 1, total: 3 })}
            </p>
            <p
              className={cn(
                "text-xs leading-relaxed",
                canContinue ? "text-on-surface-variant" : "text-warning"
              )}
            >
              {hint ?? tSteps("continueReady")}
            </p>
          </div>
        </div>

        <Button
          type="button"
          size="sm"
          className="gap-1.5 h-9 w-full sm:w-auto shrink-0"
          disabled={!canContinue}
          onClick={onContinue}
        >
          {tSteps(CONTINUE_LABEL_KEY[step])}
          <ArrowRight className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
