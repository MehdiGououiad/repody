"use client";

import { useTranslations } from "next-intl";
import { Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ConditionPreview } from "@/components/workflow/condition-builder-preview";
import { ConditionRow } from "@/components/workflow/condition-builder-row";
import {
  newCondition,
  type ConditionFieldOption,
} from "@/components/workflow/condition-builder-model";
import type { RuleCondition } from "@/lib/types";
import type { TableFieldOption } from "@/lib/rules/document-fields";

export { conditionToString, conditionsToExpression, fieldToken } from "@/lib/rules/expression";

export function ConditionBuilder({
  conditions,
  fields,
  tableFields,
  onConditionsChange,
}: {
  conditions: RuleCondition[];
  fields: ConditionFieldOption[];
  tableFields: TableFieldOption[];
  onConditionsChange: (conditions: RuleCondition[]) => void;
}) {
  const t = useTranslations("workflows.builder.rules.conditions");

  const update = (id: string, patch: Partial<RuleCondition>) =>
    onConditionsChange(
      conditions.map((condition) =>
        condition.id === id ? { ...condition, ...patch } : condition
      )
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
        <ConditionPreview conditions={conditions} />
      </div>
    </div>
  );
}
