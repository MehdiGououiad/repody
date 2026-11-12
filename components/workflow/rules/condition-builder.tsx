"use client";

import { Code2, Plus } from "lucide-react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { ConditionRow } from "@/components/workflow/rules/condition-builder-row";
import { useCatalog } from "@/lib/hooks/use-catalog";
import { isTouched } from "@/lib/rules/conditions";
import type { FieldOption, TableOption } from "@/lib/rules/document-fields";
import type { RuleCondition } from "@/lib/types";
import { newCondition } from "@/lib/workflow/new-items";

/** Each condition as the API reads it (`checks`, aligned by index), or a hint while incomplete. */
function ConditionPreview({
  conditions,
  checks,
}: {
  conditions: RuleCondition[];
  checks: string[];
}) {
  const t = useTranslations("workflows.builder.rules.conditions");
  if (checks.some(Boolean)) {
    return (
      <div className="rounded-lg border border-line bg-panel px-3 py-2 space-y-1.5">
        <p className="text-2xs text-ink-3">{t("separateChecksHint")}</p>
        {conditions.map((condition, index) =>
          checks[index] ? (
            <div key={condition.id} className="flex items-start gap-2">
              <Code2 className="h-3.5 w-3.5 text-ink-3 mt-0.5 shrink-0" />
              <code className="text-2xs font-mono text-ink-3 break-all">
                {t("checkN", { n: index + 1 })}: {checks[index]}
              </code>
            </div>
          ) : null
        )}
      </div>
    );
  }
  if (conditions.some(isTouched)) {
    return (
      <p className="text-2xs text-fail-ink rounded-lg border border-fail/30 bg-fail/5 px-3 py-2">
        {t("expressionIncomplete")}
      </p>
    );
  }
  return null;
}

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
  if (!catalog) return <div className="h-14 rounded-lg bg-raised animate-pulse" />;

  return (
    <div className="space-y-2">
      {conditions.map((condition, index) => (
        <div key={condition.id}>
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
          {index < conditions.length - 1 ? (
            <div className="flex items-center gap-2 py-1 pl-3">
              <div className="h-px flex-1 bg-line" />
              <span className="text-2xs font-semibold text-ink-3 px-2">{t("alsoCheck")}</span>
              <div className="h-px flex-1 bg-line" />
            </div>
          ) : null}
        </div>
      ))}
      <Button
        variant="outline"
        size="sm"
        className="w-full h-8 text-xs"
        onClick={() => onConditionsChange([...conditions, newCondition()])}
      >
        <Plus className="h-3.5 w-3.5" />
        {t("addCondition")}
      </Button>
      <ConditionPreview conditions={conditions} checks={checks} />
    </div>
  );
}
