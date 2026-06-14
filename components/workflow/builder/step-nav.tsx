"use client";

import { Check, CircleDot, CheckCircle2, Database, ShieldCheck, Rocket } from "lucide-react";
import { useTranslations } from "next-intl";
import { cn } from "@/lib/utils";
import { syncRuleBodies } from "@/lib/rules/sync-rules";
import type { DocumentDef, WorkflowRule } from "@/lib/types";

export type BuilderStep = 0 | 1 | 2;

export function stepComplete(
  step: BuilderStep,
  documents: DocumentDef[],
  rules: WorkflowRule[]
): boolean {
  if (step === 0)
    return documents.some(
      (d) => d.documentType.trim() && d.schema.some((f) => f.name.trim())
    );
  if (step === 1)
    return syncRuleBodies(rules).some((r) => r.name.trim() && r.body.trim());
  return false;
}

export const BUILDER_STEP_META = [
  { icon: Database, key: "extract" as const },
  { icon: ShieldCheck, key: "rules" as const },
  { icon: Rocket, key: "upload" as const },
] as const;

const STEP_META = BUILDER_STEP_META;

export function BuilderStepNav({
  current,
  documents,
  rules,
  onChange,
  tSteps,
  testHasResults,
}: {
  current: BuilderStep;
  documents: DocumentDef[];
  rules: WorkflowRule[];
  onChange: (s: BuilderStep) => void;
  tSteps: ReturnType<typeof useTranslations>;
  testHasResults?: boolean;
}) {
  const steps = STEP_META.map(({ icon: Icon, key }, idx) => {
    const isActive = current === idx;
    const isDone = !isActive && stepComplete(idx as BuilderStep, documents, rules);
    const isBlocked =
      (idx === 1 && !stepComplete(0, documents, rules)) ||
      (idx === 2 && !stepComplete(0, documents, rules));

    return (
      <button
        key={key}
        type="button"
        onClick={() => !isBlocked && onChange(idx as BuilderStep)}
        disabled={isBlocked}
        title={isBlocked ? tSteps("blockedHint") : undefined}
        className={cn(
          "group w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-[background-color,color,box-shadow]",
          isActive
            ? "bg-accent-blue/12 text-on-surface ring-1 ring-accent-blue/20"
            : isBlocked
              ? "opacity-40 cursor-not-allowed text-on-surface-variant"
              : "text-on-surface-variant hover:bg-surface-bright hover:text-on-surface"
        )}
      >
        <div
          className={cn(
            "size-6 rounded-full flex items-center justify-center shrink-0 text-xs font-bold transition-colors",
            isActive
              ? "bg-accent-blue text-primary-stitch shadow-[0_0_16px_-4px_var(--accent-blue-glow)]"
              : isDone
                ? "bg-success text-white"
                : "bg-surface-container-high text-on-surface-variant"
          )}
        >
          {isDone ? <Check className="h-3 w-3" /> : <Icon className="h-3 w-3" />}
        </div>
        <div className="flex-1 min-w-0">
          <p className={cn("text-[13px] font-medium truncate", isActive && "text-on-surface")}>
            {tSteps(key)}
          </p>
          <p className="text-[11px] text-on-surface-variant/70 truncate mt-0.5">
            {tSteps(`${key}Hint` as Parameters<typeof tSteps>[0])}
          </p>
        </div>
        {isActive && <CircleDot className="h-3.5 w-3.5 shrink-0 text-accent-blue" />}
        {!isActive && idx === 2 && testHasResults && (
          <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-success" />
        )}
      </button>
    );
  });

  const done = STEP_META.filter((_, i) =>
    stepComplete(i as BuilderStep, documents, rules)
  ).length;

  return (
    <div className="flex flex-col gap-1 h-full">
      <p className="text-[10px] font-semibold uppercase tracking-wider text-on-surface-variant px-3 mb-2">
        {tSteps("navTitle")}
      </p>
      {steps}
      <div className="mt-auto pt-4 border-t border-border px-3">
        <div className="flex items-center justify-between text-[11px] text-on-surface-variant mb-1.5">
          <span>{tSteps("progress")}</span>
          <span className="font-semibold">
            {done}/{STEP_META.length}
          </span>
        </div>
        <div className="w-full h-1 rounded-full bg-surface-container-high overflow-hidden">
          <div
            className="h-full rounded-full bg-accent-blue transition-[width] duration-500"
            style={{ width: `${(done / STEP_META.length) * 100}%` }}
          />
        </div>
      </div>
    </div>
  );
}
