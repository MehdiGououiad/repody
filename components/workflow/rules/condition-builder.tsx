"use client";

import { Plus } from "lucide-react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { ConditionRow } from "@/components/workflow/rules/condition-builder-row";
import { catalog } from "@/lib/catalog";
import { isTouched } from "@/lib/rules/conditions";
import type { FieldOption, TableOption } from "@/lib/rules/document-fields";
import type { RuleCondition } from "@/lib/types";
import { newCondition } from "@/lib/workflow/new-items";

export function ConditionBuilder({
  conditions,
  fields,
  tables,
  checks,
  onConditionsChange,
  onSwitchFieldToNumber,
}: {
  conditions: RuleCondition[];
  fields: FieldOption[];
  tables: TableOption[];
  checks: string[];
  onConditionsChange: (conditions: RuleCondition[]) => void;
  onSwitchFieldToNumber?: (fieldName: string) => void;
}) {
  const t = useTranslations("workflows.builder.rules.conditions");
  const incomplete = conditions.some(isTouched) && !checks.some(Boolean);

  return (
    <div className="flex flex-col gap-1.5">
      {conditions.map((condition, index) => (
        <div key={condition.id} className="flex flex-col gap-1">
          {index > 0 ? <span className="text-xs text-ink-3">{t("alsoCheck")}</span> : null}
          <ConditionRow
            condition={condition}
            fields={fields}
            tables={tables}
            catalog={catalog}
            onChange={(next) =>
              onConditionsChange(conditions.map((c) => (c.id === condition.id ? next : c)))
            }
            onRemove={() => onConditionsChange(conditions.filter((c) => c.id !== condition.id))}
            onSwitchFieldToNumber={onSwitchFieldToNumber}
            canRemove={conditions.length > 1}
          />
        </div>
      ))}
      {incomplete ? <p className="text-xs text-warn-ink">{t("expressionIncomplete")}</p> : null}
      <Button
        variant="ghost"
        size="sm"
        className="-ms-2 self-start"
        onClick={() => onConditionsChange([...conditions, newCondition()])}
      >
        <Plus />
        {t("addCondition")}
      </Button>
    </div>
  );
}
