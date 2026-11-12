"use client";

import { Code } from "lucide-react";
import { useTranslations } from "next-intl";
import { SectionHeading } from "@/components/layout/section-heading";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useRuleValidation } from "@/lib/hooks/use-rule-validation";
import type { DocumentDef, WorkflowRule } from "@/lib/types";
import { newRule } from "@/lib/workflow/new-items";
import { RuleCard } from "./rule-card";

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
  const remove = (id: string) => onChange(rules.filter((r) => r.id !== id));

  const intraCount = rules.filter((r) => r.scope === "intra").length;
  const crossCount = rules.filter((r) => r.scope === "cross").length;

  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <SectionHeading title={t("title")} description={t("hint")} eyebrow={t("eyebrow")} />
        <p className="text-xs text-ink-3/90 rounded-lg border border-line/70 bg-raised/80 px-3 py-2">
          {t("runsOnOcr")}
        </p>
      </div>

      <div className="flex items-center justify-between">
        <p className="text-sm font-semibold">
          {t("active")} ({rules.length})
        </p>
        <Badge variant="secondary" className="text-2xs">
          {intraCount} {t("scopeIntraShort")} · {crossCount} {t("scopeCrossShort")}
        </Badge>
      </div>

      <div className="space-y-3">
        {rules.length === 0 ? (
          <div className="border-2 border-dashed border-line rounded-xl py-12 text-center text-sm text-ink-3">
            {t("emptyActive")}
          </div>
        ) : (
          rules.map((r) => (
            <RuleCard
              key={r.id}
              rule={r}
              documents={documents}
              validation={validationById[r.id]}
              onChange={(patch) => updateRule(r.id, patch)}
              onRemove={() => remove(r.id)}
            />
          ))
        )}
        <Button
          variant="outline"
          size="sm"
          onClick={() => onChange([...rules, newRule(documents)])}
          className="w-full"
        >
          <Code className="h-3.5 w-3.5" />
          {t("addLogic")}
        </Button>
      </div>
    </div>
  );
}
