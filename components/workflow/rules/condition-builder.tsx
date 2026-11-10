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
      <div className="rounded-lg border border-border bg-surface-container-lowest px-3 py-2 space-y-1.5">
        <p className="text-[10px] text-on-surface-variant">{t("separateChecksHint")}</p>
        {conditions.map((condition, index) =>
          checks[index] ? (
            <div key={condition.id} className="flex items-start gap-2">
              <Code2 className="h-3.5 w-3.5 text-on-surface-variant mt-0.5 shrink-0" />
              <code className="text-[11px] font-mono text-on-surface-variant break-all">
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
      <p className="text-[11px] text-danger rounded-lg border border-danger/30 bg-danger/5 px-3 py-2">
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
  if (!catalog) return <div className="h-14 rounded-lg bg-surface-container-low animate-pulse" />;

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
              <div className="h-px flex-1 bg-border" />
              <span className="text-[10px] font-semibold uppercase tracking-wide text-on-surface-variant px-2">
                {t("alsoCheck")}
              </span>
              <div className="h-px flex-1 bg-border" />
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
