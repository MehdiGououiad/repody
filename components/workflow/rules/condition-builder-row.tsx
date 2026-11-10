"use client";

import { Trash2 } from "lucide-react";
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

function Slot({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-[9px] uppercase tracking-wider font-semibold text-on-surface-variant">
        {label}
      </span>
      {children}
    </div>
  );
}

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
    <div className="flex flex-wrap items-start gap-2 p-3 rounded-lg bg-surface-container-low border border-border group">
      <Slot label={t("left")}>
        <ConditionLeft
          value={left}
          fields={fields}
          tables={tables}
          catalog={catalog}
          onChange={(next) => onChange({ ...condition, left: next })}
        />
      </Slot>

      <Slot label={t("operator")}>
        <Select value={operator} onValueChange={(value) => setOperator(value as ComparisonOp)}>
          <SelectTrigger className="h-8 w-44 text-xs">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectGroup>
              <SelectLabel className="text-[10px]">{t("comparison")}</SelectLabel>
              {operators
                .filter((op) => !isPresenceOp(op.value, catalog))
                .map((op) => (
                  <SelectItem key={op.value} value={op.value} className="text-xs font-mono">
                    {t(op.key)}
                  </SelectItem>
                ))}
            </SelectGroup>
            <SelectGroup>
              <SelectLabel className="text-[10px]">{t("existence")}</SelectLabel>
              {operators
                .filter((op) => isPresenceOp(op.value, catalog))
                .map((op) => (
                  <SelectItem key={op.value} value={op.value} className="text-xs">
                    {t(op.key)}
                  </SelectItem>
                ))}
            </SelectGroup>
          </SelectContent>
        </Select>
      </Slot>

      {right ? (
        <Slot label={t("right")}>
          <OperandPicker
            operand={right}
            fields={fields.filter((field) => field.type !== catalog.tableType)}
            onChange={(next) => onChange({ ...condition, right: next })}
            inputKind={literalInputKind(leftType ?? rightType, catalog)}
          />
        </Slot>
      ) : null}

      {canRemove ? (
        <Button
          variant="ghost"
          size="icon"
          className="mt-5 h-8 w-8 opacity-0 group-hover:opacity-100 focus-visible:opacity-100 text-outline hover:text-danger"
          onClick={onRemove}
          aria-label={tCommon("remove")}
        >
          <Trash2 className="h-3.5 w-3.5" />
        </Button>
      ) : null}
    </div>
  );
}
