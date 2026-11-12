"use client";

import { Check } from "lucide-react";
import { useTranslations } from "next-intl";
import {
  BUILDER_STEP_META,
  type BuilderStep,
  stepBlocked,
  stepComplete,
} from "@/components/workflow/builder/step-nav";
import type { DocumentDef, WorkflowRule } from "@/lib/types";
import { cn } from "@/lib/utils";

export function BuilderMobileSteps({
  step,
  documents,
  rules,
  onChange,
}: {
  step: BuilderStep;
  documents: DocumentDef[];
  rules: WorkflowRule[];
  onChange: (step: BuilderStep) => void;
}) {
  const tSteps = useTranslations("workflows.builder.steps");

  return (
    <div className="md:hidden flex border-t border-accent/20 bg-panel/90 shrink-0">
      {BUILDER_STEP_META.map(({ icon: Icon, key }, idx) => {
        const isActive = step === idx;
        const isDone = !isActive && stepComplete(idx as BuilderStep, documents, rules);
        const isBlocked = stepBlocked(idx as BuilderStep, documents, rules);
        return (
          <button
            key={key}
            type="button"
            onClick={() => !isBlocked && onChange(idx as BuilderStep)}
            disabled={isBlocked}
            title={isBlocked ? tSteps("blockedHint") : undefined}
            className={cn(
              "flex-1 flex flex-col items-center gap-1 py-2.5 text-2xs font-medium transition-colors",
              isActive
                ? "text-ink border-t-2 border-accent -mt-px"
                : isBlocked
                  ? "text-ink-3 opacity-40 cursor-not-allowed"
                  : "text-ink-3"
            )}
          >
            <div
              className={cn(
                "size-5 rounded-full flex items-center justify-center",
                isDone ? "bg-pass text-white" : ""
              )}
            >
              {isDone ? <Check className="h-3 w-3" /> : <Icon className="h-3.5 w-3.5" />}
            </div>
            {tSteps(key)}
          </button>
        );
      })}
    </div>
  );
}
