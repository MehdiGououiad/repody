"use client";

import { Plus } from "lucide-react";
import { useTranslations } from "next-intl";
import { SectionHeading } from "@/components/layout/section-heading";
import { Button } from "@/components/ui/button";
import { useRuleValidation } from "@/lib/hooks/use-rule-validation";
import type { DocumentDef, WorkflowRule } from "@/lib/types";
import { newRule } from "@/lib/workflow/new-items";
import { RuleCard } from "./rule-card";

/** The checks every run must pass, on one document or across two. */
export function RulesPanel({
  rules,
  documents,
  onChange,
}: {
  rules: WorkflowRule[];
  documents: DocumentDef[];
  onChange: (rules: WorkflowRule[]) => void;
}) {
  const t = useTranslations("workflows.builder.rules");
  const validationById = useRuleValidation(documents, rules);
  const updateRule = (id: string, patch: Partial<WorkflowRule>) =>
    onChange(rules.map((r) => (r.id === id ? { ...r, ...patch } : r)));

  return (
    <div className="flex flex-col gap-8">
      <SectionHeading title={t("title")} description={t("hint")} />
      {rules.length ? (
        <div className="flex flex-col gap-4">
          {rules.map((rule) => (
            <RuleCard
              key={rule.id}
              rule={rule}
              documents={documents}
              validation={validationById[rule.id]}
              onChange={(patch) => updateRule(rule.id, patch)}
              onRemove={() => onChange(rules.filter((r) => r.id !== rule.id))}
            />
          ))}
        </div>
      ) : (
        <p className="text-sm text-ink-3">{t("emptyActive")}</p>
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
