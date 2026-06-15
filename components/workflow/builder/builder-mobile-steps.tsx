"use client";

import { useTranslations } from "next-intl";
import { Check } from "lucide-react";
import { cn } from "@/lib/utils";
import {
  BUILDER_STEP_META,
  stepBlocked,
  stepComplete,
  type BuilderStep,
} from "@/components/workflow/builder/step-nav";
import type { DocumentDef, WorkflowRule } from "@/lib/types";

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
    <div className="md:hidden flex border-t border-accent-blue/20 bg-card/90 backdrop-blur shrink-0">
      {BUILDER_STEP_META.map(({ icon: Icon, key }, idx) => {
        const isActive = step === idx;
        const isDone =
          !isActive && stepComplete(idx as BuilderStep, documents, rules);
        const isBlocked = stepBlocked(idx as BuilderStep, documents, rules);
        return (
          <button
            key={key}
            type="button"
            onClick={() => !isBlocked && onChange(idx as BuilderStep)}
            disabled={isBlocked}
            title={isBlocked ? tSteps("blockedHint") : undefined}
            className={cn(
              "flex-1 flex flex-col items-center gap-1 py-2.5 text-[10px] font-medium transition-colors",
              isActive
                ? "text-primary border-t-2 border-primary -mt-px"
                : isBlocked
                  ? "text-on-surface-variant opacity-40 cursor-not-allowed"
                  : "text-on-surface-variant"
            )}
          >
            <div
              className={cn(
                "size-5 rounded-full flex items-center justify-center",
                isDone ? "bg-success text-white" : ""
              )}
            >
              {isDone ? (
                <Check className="h-3 w-3" />
              ) : (
                <Icon className="h-3.5 w-3.5" />
              )}
            </div>
            {tSteps(key)}
          </button>
        );
      })}
    </div>
  );
}
