"use client";

import { Plus } from "lucide-react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ConditionRow } from "@/components/workflow/rules/condition-builder-row";
import { useCatalog } from "@/lib/hooks/use-catalog";
import { isTouched } from "@/lib/rules/conditions";
import type { FieldOption, TableOption } from "@/lib/rules/document-fields";
import type { RuleCondition } from "@/lib/types";
import { newCondition } from "@/lib/workflow/new-items";

/** The conditions of a rule, joined by "and", each with the check the API will run under it. */
export function ConditionBuilder({
  conditions,
  fields,
  tables,
  checks,
  onConditionsChange,
}: {
  conditions: RuleCondition[];
  fields: FieldOption[];
  tables: TableOption[];
  checks: string[];
  onConditionsChange: (conditions: RuleCondition[]) => void;
}) {
  const t = useTranslations("workflows.builder.rules.conditions");
  const catalog = useCatalog();
  if (!catalog) return <Skeleton className="h-8" />;
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
            canRemove={conditions.length > 1}
          />
          {checks[index] ? (
            <code className="break-all font-mono text-xs text-ink-4">{checks[index]}</code>
          ) : null}
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
