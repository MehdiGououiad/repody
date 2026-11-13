"use client";

import { Plus } from "lucide-react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { useRuleValidation } from "@/lib/hooks/use-rule-validation";
import type { DocumentDef, RunAuditRule, WorkflowRule } from "@/lib/types";
import { newRule } from "@/lib/workflow/new-items";
import { RuleCard } from "./rule-card";

/** The checks every run must pass, on one document or across two. */
export function RulesPanel({
  rules,
  documents,
  results,
  onChange,
}: {
  rules: WorkflowRule[];
  documents: DocumentDef[];
  results?: RunAuditRule[];
  onChange: (rules: WorkflowRule[]) => void;
}) {
  const t = useTranslations("workflows.builder.rules");
  const validationById = useRuleValidation(documents, rules);
  const updateRule = (id: string, patch: Partial<WorkflowRule>) =>
    onChange(rules.map((r) => (r.id === id ? { ...r, ...patch } : r)));

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h2 className="text-[15px] font-semibold text-ink">{t("title")}</h2>
        <p className="mt-1 text-[13px] text-ink-3">{t("hint")}</p>
      </div>
      {rules.length ? (
        <div className="flex flex-col gap-3">
          {rules.map((rule) => (
            <RuleCard
              key={rule.id}
              rule={rule}
              documents={documents}
              validation={validationById[rule.id]}
              result={results?.find((r) => r.ruleId === rule.id)}
              onChange={(patch) => updateRule(rule.id, patch)}
              onRemove={() => onChange(rules.filter((r) => r.id !== rule.id))}
            />
          ))}
        </div>
      ) : (
        <p className="rounded-lg bg-raised px-4 py-6 text-[13px] text-ink-3 shadow-[0_0_0_1px_var(--line)]">
          {t("emptyActive")}
        </p>
      )}
      <Button
        variant="secondary"
        className="self-start"
        onClick={() => onChange([...rules, newRule(documents)])}
      >
        <Plus />
        {t("addLogic")}
      </Button>
    </div>
  );
}
