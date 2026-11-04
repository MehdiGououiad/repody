"use client";

import { Plus } from "lucide-react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { ConditionPreview } from "@/components/workflow/rules/condition-builder-preview";
import { ConditionRow } from "@/components/workflow/rules/condition-builder-row";
import type { DocumentFieldOption, TableFieldOption } from "@/lib/rules/document-fields";
import type { RuleCondition } from "@/lib/types";
import { newCondition } from "@/lib/workflow/new-items";

export function ConditionBuilder({
  conditions,
  fields,
  tableFields,
  checks,
  onConditionsChange,
}: {
  conditions: RuleCondition[];
  fields: DocumentFieldOption[];
  tableFields: TableFieldOption[];
  checks: string[];
  onConditionsChange: (conditions: RuleCondition[]) => void;
}) {
  const t = useTranslations("workflows.builder.rules.conditions");

  const update = (id: string, patch: Partial<RuleCondition>) =>
    onConditionsChange(
      conditions.map((condition) => (condition.id === id ? { ...condition, ...patch } : condition))
    );

  const remove = (id: string) =>
    onConditionsChange(conditions.filter((condition) => condition.id !== id));

  const add = () => onConditionsChange([...conditions, newCondition()]);

  return (
    <div className="space-y-2">
      {conditions.map((condition, index) => (
        <div key={condition.id}>
          <ConditionRow
            condition={condition}
            fields={fields}
            tableFields={tableFields}
            onChange={(patch) => update(condition.id, patch)}
            onRemove={() => remove(condition.id)}
            canRemove={conditions.length > 1}
          />
          {index < conditions.length - 1 ? (
            <div className="flex items-center gap-2 py-1 pl-3">
              <div className="h-px flex-1 bg-border" />
              <span className="text-[10px] font-semibold uppercase tracking-wide text-on-surface-variant px-2">
                {t("alsoCheck")}
              </span>
              <div className="h-px flex-1 bg-border" />
            </div>
          ) : null}
        </div>
      ))}

      <Button variant="outline" size="sm" className="w-full h-8 text-xs" onClick={add}>
        <Plus className="h-3.5 w-3.5" />
        {t("addCondition")}
      </Button>

      <div className="space-y-1">
        <ConditionPreview conditions={conditions} checks={checks} />
      </div>
    </div>
  );
}
