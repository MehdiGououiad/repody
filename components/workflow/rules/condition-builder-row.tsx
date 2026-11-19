"use client";

import { X } from "lucide-react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectGroupLabel,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { StatusGlyph } from "@/components/ui/status-glyph";
import { ConditionLeft } from "@/components/workflow/rules/condition-left";
import { OperandPicker } from "@/components/workflow/rules/condition-operand-picker";
import { literal } from "@/lib/rules/conditions";
import { type FieldOption, type TableOption, typeOf } from "@/lib/rules/document-fields";
import {
  isPresenceOp,
  literalInputKind,
  operatorsFor,
  textComparedWithNumber,
} from "@/lib/rules/operators";
import type { Catalog, ComparisonOp, RuleCondition } from "@/lib/types";

export function ConditionRow({
  condition,
  fields,
  tables,
  catalog,
  onChange,
  onRemove,
  onSwitchFieldToNumber,
  canRemove,
}: {
  condition: RuleCondition;
  fields: FieldOption[];
  tables: TableOption[];
  catalog: Catalog;
  onChange: (condition: RuleCondition) => void;
  onRemove: () => void;
  onSwitchFieldToNumber?: (fieldName: string) => void;
  canRemove: boolean;
}) {
  const t = useTranslations("workflows.builder.rules.conditions");
  const tCommon = useTranslations("common");
  const { left, right, operator } = condition;
  // Arithmetic and aggregates produce numbers; a literal is read as the left side's type.
  const leftType = left.kind === "field" ? typeOf(left.field, fields) : "number";
  const rightType = right?.kind === "field" ? typeOf(right.field, fields) : undefined;
  const operators = operatorsFor(leftType, catalog);
  const textNumberField = textComparedWithNumber(condition, fields, catalog);
  const setOperator = (next: ComparisonOp) =>
    onChange({
      ...condition,
      operator: next,
      right: isPresenceOp(next, catalog) ? null : (right ?? literal()),
    });

  return (
    <div className="flex flex-col gap-1.5">
      <div className="group flex flex-wrap items-center gap-1.5">
        <ConditionLeft
          value={left}
          fields={fields}
          tables={tables}
          catalog={catalog}
          onChange={(next) => onChange({ ...condition, left: next })}
        />
        <Select
          value={operator}
          onValueChange={(value: string | null) =>
            value !== null && setOperator(value as ComparisonOp)
          }
        >
          <SelectTrigger className="w-auto min-w-32" aria-label={t("operator")}>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectGroup>
              <SelectGroupLabel>{t("comparison")}</SelectGroupLabel>
              {operators
                .filter((op) => !isPresenceOp(op.value, catalog))
                .map((op) => (
                  <SelectItem key={op.value} value={op.value}>
                    {t(op.key)}
                  </SelectItem>
                ))}
            </SelectGroup>
            <SelectGroup>
              <SelectGroupLabel>{t("existence")}</SelectGroupLabel>
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
            className="text-ink-4 hover:text-fail-ink pointer-fine:opacity-0 pointer-fine:group-focus-within:opacity-100 pointer-fine:group-hover:opacity-100"
            onClick={onRemove}
            aria-label={tCommon("remove")}
          >
            <X />
          </Button>
        ) : null}
      </div>
      {textNumberField ? (
        <div
          role="status"
          className="flex flex-wrap items-center gap-2 rounded-md bg-warn-wash/60 px-2.5 py-1.5 text-xs text-warn-ink"
        >
          <StatusGlyph status="warning" className="size-3.5" />
          <span>{t("textComparedWithNumber", { field: textNumberField })}</span>
          {onSwitchFieldToNumber ? (
            <Button
              variant="secondary"
              size="xs"
              onClick={() => onSwitchFieldToNumber(textNumberField)}
            >
              {t("useNumberType")}
            </Button>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
