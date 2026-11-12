"use client";

import { X } from "lucide-react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ConditionLeft } from "@/components/workflow/rules/condition-left";
import { OperandPicker } from "@/components/workflow/rules/condition-operand-picker";
import { literal } from "@/lib/rules/conditions";
import { type FieldOption, type TableOption, typeOf } from "@/lib/rules/document-fields";
import { isPresenceOp, literalInputKind, operatorsFor } from "@/lib/rules/operators";
import type { Catalog, ComparisonOp, RuleCondition } from "@/lib/types";

/** One condition, read left to right: what is checked, how, against what. */
export function ConditionRow({
  condition,
  fields,
  tables,
  catalog,
  onChange,
  onRemove,
  canRemove,
}: {
  condition: RuleCondition;
  fields: FieldOption[];
  tables: TableOption[];
  catalog: Catalog;
  onChange: (condition: RuleCondition) => void;
  onRemove: () => void;
  canRemove: boolean;
}) {
  const t = useTranslations("workflows.builder.rules.conditions");
  const tCommon = useTranslations("common");
  const { left, right, operator } = condition;
  // Arithmetic and aggregates produce numbers; a literal is read as the left side's type.
  const leftType = left.kind === "field" ? typeOf(left.field, fields) : "number";
  const rightType = right?.kind === "field" ? typeOf(right.field, fields) : undefined;
  const operators = operatorsFor(leftType, catalog);
  const setOperator = (next: ComparisonOp) =>
    onChange({
      ...condition,
      operator: next,
      right: isPresenceOp(next, catalog) ? null : (right ?? literal()),
    });

  return (
    <div className="group flex flex-wrap items-center gap-1.5">
      <ConditionLeft
        value={left}
        fields={fields}
        tables={tables}
        catalog={catalog}
        onChange={(next) => onChange({ ...condition, left: next })}
      />
      <Select value={operator} onValueChange={(value) => setOperator(value as ComparisonOp)}>
        <SelectTrigger className="w-auto min-w-32" aria-label={t("operator")}>
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectGroup>
            <SelectLabel>{t("comparison")}</SelectLabel>
            {operators
              .filter((op) => !isPresenceOp(op.value, catalog))
              .map((op) => (
                <SelectItem key={op.value} value={op.value}>
                  {t(op.key)}
                </SelectItem>
              ))}
          </SelectGroup>
          <SelectGroup>
            <SelectLabel>{t("existence")}</SelectLabel>
            {operators
              .filter((op) => isPresenceOp(op.value, catalog))
              .map((op) => (
                <SelectItem key={op.value} value={op.value}>
                  {t(op.key)}
                </SelectItem>
              ))}
          </SelectGroup>
        </SelectContent>
      </Select>
      {right ? (
        <OperandPicker
          operand={right}
          fields={fields.filter((field) => field.type !== catalog.tableType)}
          onChange={(next) => onChange({ ...condition, right: next })}
          inputKind={literalInputKind(leftType ?? rightType, catalog)}
        />
      ) : null}
      {canRemove ? (
        <Button
          variant="ghost"
          size="icon-sm"
          className="text-ink-4 hover:text-fail-ink md:opacity-0 md:group-focus-within:opacity-100 md:group-hover:opacity-100"
          onClick={onRemove}
          aria-label={tCommon("remove")}
        >
          <X />
        </Button>
      ) : null}
    </div>
  );
}
