"use client";

import { useTranslations } from "next-intl";
import { Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  ARITH_OPS,
  NO_RIGHT,
  type ConditionFieldOption,
} from "@/components/workflow/condition-builder-model";
import {
  comparisonOpsForTemplateType,
  literalInputKindForTemplateType,
  resolveFieldTemplateType,
  type LiteralInputKind,
} from "@/lib/rules/condition-input-kind";
import { cn } from "@/lib/utils";
import type { ArithmeticOp, ComparisonOp, ConditionOperand, RuleCondition, TableAggregateLeft } from "@/lib/types";
import type { TableFieldOption } from "@/lib/rules/document-fields";

function literalPlaceholderForKind(
  kind: LiteralInputKind,
  t: ReturnType<typeof useTranslations>
): string | undefined {
  switch (kind) {
    case "date":
      return t("literalDatePlaceholder");
    case "datetime-local":
      return t("literalDateTimePlaceholder");
    case "time":
      return t("literalTimePlaceholder");
    case "number":
      return t("literalNumberPlaceholder");
    default:
      return t("literalPlaceholder");
  }
}

function LiteralValueInput({
  value,
  onChange,
  inputKind,
  placeholder,
}: {
  value: string;
  onChange: (value: string) => void;
  inputKind: LiteralInputKind;
  placeholder?: string;
}) {
  if (inputKind === "boolean") {
    return (
      <Select value={value || "true"} onValueChange={onChange}>
        <SelectTrigger className="h-8 text-xs w-32">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="true" className="text-xs font-mono">
            true
          </SelectItem>
          <SelectItem value="false" className="text-xs font-mono">
            false
          </SelectItem>
        </SelectContent>
      </Select>
    );
  }

  return (
    <Input
      type={inputKind === "text" ? "text" : inputKind}
      value={value}
      onChange={(event) => onChange(event.target.value)}
      placeholder={placeholder}
      step={inputKind === "number" ? "any" : undefined}
      className={cn(
        "h-8 text-xs font-mono",
        inputKind === "datetime-local" ? "w-48" : "w-40"
      )}
    />
  );
}

function OperandPicker({
  operand,
  fields,
  onChange,
  placeholder,
  allowLiteral = true,
  literalInputKind = "text",
}: {
  operand: ConditionOperand;
  fields: ConditionFieldOption[];
  onChange: (operand: ConditionOperand) => void;
  placeholder?: string;
  allowLiteral?: boolean;
  literalInputKind?: LiteralInputKind;
}) {
  const t = useTranslations("workflows.builder.rules.conditions");

  if (operand.kind === "literal") {
    return (
      <div className="flex items-center gap-1">
        <LiteralValueInput
          value={operand.value}
          onChange={(value) => onChange({ kind: "literal", value })}
          inputKind={literalInputKind}
          placeholder={literalPlaceholderForKind(literalInputKind, t)}
        />
        {fields.length > 0 ? (
          <Button
            variant="ghost"
            size="sm"
            className="h-8 text-[10px] text-on-surface-variant px-2"
            onClick={() => onChange({ kind: "field", value: fields[0]?.token ?? "" })}
          >
            {t("switchToField")}
          </Button>
        ) : null}
      </div>
    );
  }

  return (
    <div className="flex items-center gap-1">
      <Select
        value={operand.value}
        onValueChange={(value) => onChange({ kind: "field", value })}
      >
        <SelectTrigger className="h-8 text-xs w-40 font-mono">
          <SelectValue placeholder={placeholder ?? t("pickField")} />
        </SelectTrigger>
        <SelectContent>
          {fields.map((field) => (
            <SelectItem key={field.token} value={field.token} className="text-xs font-mono">
              {field.label}
            </SelectItem>
          ))}
          {fields.length === 0 ? (
            <div className="px-3 py-2 text-xs text-on-surface-variant italic">
              {t("noFields")}
            </div>
          ) : null}
        </SelectContent>
      </Select>
      {allowLiteral ? (
        <Button
          variant="ghost"
          size="sm"
          className="h-8 text-[10px] text-on-surface-variant px-2"
          onClick={() => onChange({ kind: "literal", value: "" })}
        >
          {t("switchToValue")}
        </Button>
      ) : null}
    </div>
  );
}

export function ConditionRow({
  condition,
  fields,
  tableFields,
  onChange,
  onRemove,
  canRemove,
}: {
  condition: RuleCondition;
  fields: ConditionFieldOption[];
  tableFields: TableFieldOption[];
  onChange: (patch: Partial<RuleCondition>) => void;
  onRemove: () => void;
  canRemove: boolean;
}) {
  const t = useTranslations("workflows.builder.rules.conditions");
  const tCommon = useTranslations("common");
  const useAggregate = Boolean(condition.tableAggregate);
  const activeTable =
    tableFields.find((table) => table.token === condition.tableAggregate?.tableField) ??
    tableFields[0];
  const hasArith = Boolean(condition.arithmeticOp) && !useAggregate;
  const noRight = NO_RIGHT.includes(condition.operator);
  const leftTemplateType =
    condition.left.kind === "field"
      ? resolveFieldTemplateType(condition.left.value, fields)
      : undefined;
  const rightTemplateType =
    condition.right?.kind === "field"
      ? resolveFieldTemplateType(condition.right.value, fields)
      : undefined;
  const literalInputKind = literalInputKindForTemplateType(
    leftTemplateType ?? rightTemplateType
  );
  const comparisonOps = comparisonOpsForTemplateType(leftTemplateType).map((definition) => ({
    value: definition.value,
    label: t(definition.key as Parameters<typeof t>[0]),
    noRight: definition.noRight,
  }));

  const toggleArith = () => {
    if (hasArith) {
      onChange({ arithmeticOp: undefined, leftExtra: undefined });
    } else {
      onChange({ arithmeticOp: "+", leftExtra: { kind: "field", value: "" } });
    }
  };

  const toggleAggregate = () => {
    if (useAggregate) {
      onChange({ tableAggregate: undefined, left: { kind: "field", value: "" } });
      return;
    }
    const table = tableFields[0];
    onChange({
      tableAggregate: {
        fn: "sum_rows_where",
        tableField: table?.token ?? "",
        amountColumn: "",
        filterColumn: "",
        filterContains: "",
      },
      arithmeticOp: undefined,
      leftExtra: undefined,
    });
  };

  const updateAggregate = (patch: Partial<TableAggregateLeft>) => {
    if (!condition.tableAggregate) return;
    onChange({
      tableAggregate: {
        ...condition.tableAggregate,
        ...patch,
      },
    });
  };

  return (
    <div className="flex flex-wrap items-start gap-2 p-3 rounded-lg bg-surface-container-low border border-border group">
      <div className="flex flex-col gap-1">
        <span className="text-[9px] uppercase tracking-wider font-semibold text-on-surface-variant">
          {t("left")}
        </span>
        <div className="flex items-center gap-1">
          {tableFields.length > 0 ? (
            <button
              type="button"
              onClick={toggleAggregate}
              className={cn(
                "h-8 px-2 rounded border text-[10px] font-semibold uppercase tracking-wide shrink-0",
                useAggregate
                  ? "bg-primary/10 border-primary/30 text-primary"
                  : "bg-surface-container-high border-border text-on-surface-variant hover:border-outline"
              )}
            >
              {t("tableAggregate")}
            </button>
          ) : null}
          {useAggregate ? (
            <div className="flex flex-wrap items-center gap-1">
              <Select
                value={condition.tableAggregate?.fn ?? "sum_rows_where"}
                onValueChange={(value) =>
                  updateAggregate({ fn: value as TableAggregateLeft["fn"] })
                }
              >
                <SelectTrigger className="h-8 w-36 text-xs">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="sum_rows" className="text-xs">
                    {t("aggSumRows")}
                  </SelectItem>
                  <SelectItem value="sum_rows_where" className="text-xs">
                    {t("aggSumRowsWhere")}
                  </SelectItem>
                  <SelectItem value="count_rows_where" className="text-xs">
                    {t("aggCountRowsWhere")}
                  </SelectItem>
                </SelectContent>
              </Select>
              <Select
                value={condition.tableAggregate?.tableField ?? ""}
                onValueChange={(value) => {
                  updateAggregate({
                    tableField: value,
                    amountColumn: "",
                    filterColumn: "",
                  });
                }}
              >
                <SelectTrigger className="h-8 w-40 text-xs font-mono">
                  <SelectValue placeholder={t("pickTable")} />
                </SelectTrigger>
                <SelectContent>
                  {tableFields.map((table) => (
                    <SelectItem key={table.token} value={table.token} className="text-xs font-mono">
                      {table.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {condition.tableAggregate?.fn !== "count_rows_where" ? (
                <Select
                  value={condition.tableAggregate?.amountColumn ?? ""}
                  onValueChange={(value) => updateAggregate({ amountColumn: value })}
                >
                  <SelectTrigger className="h-8 w-32 text-xs font-mono">
                    <SelectValue placeholder={t("amountColumn")} />
                  </SelectTrigger>
                  <SelectContent>
                    {(activeTable?.columns ?? []).map((column) => (
                      <SelectItem key={column.name} value={column.name} className="text-xs font-mono">
                        {column.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              ) : null}
              {condition.tableAggregate?.fn !== "sum_rows" ? (
                <>
                  <Select
                    value={condition.tableAggregate?.filterColumn ?? ""}
                    onValueChange={(value) => updateAggregate({ filterColumn: value })}
                  >
                    <SelectTrigger className="h-8 w-32 text-xs font-mono">
                      <SelectValue placeholder={t("filterColumn")} />
                    </SelectTrigger>
                    <SelectContent>
                      {(activeTable?.columns ?? []).map((column) => (
                        <SelectItem key={column.name} value={column.name} className="text-xs font-mono">
                          {column.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <Input
                    value={condition.tableAggregate?.filterContains ?? ""}
                    onChange={(event) => updateAggregate({ filterContains: event.target.value })}
                    placeholder={t("filterContains")}
                    className="h-8 w-44 text-xs font-mono"
                  />
                </>
              ) : null}
            </div>
          ) : (
            <>
              <OperandPicker
                operand={condition.left}
                fields={fields.filter((field) => !field.tableParent)}
                onChange={(operand) => onChange({ left: operand })}
                allowLiteral={false}
                placeholder={t("pickField")}
              />
              <button
                onClick={toggleArith}
                className={cn(
                  "h-8 w-8 rounded border flex items-center justify-center text-[11px] font-bold transition-colors shrink-0",
                  hasArith
                    ? "bg-primary/10 border-primary/30 text-primary"
                    : "bg-surface-container-high border-border text-on-surface-variant hover:border-outline"
                )}
                title={hasArith ? t("removeArith") : t("addArith")}
              >
                +
              </button>
            </>
          )}
        </div>

        {hasArith ? (
          <div className="flex items-center gap-1 pl-1">
            <Select
              value={condition.arithmeticOp ?? "+"}
              onValueChange={(value) => onChange({ arithmeticOp: value as ArithmeticOp })}
            >
              <SelectTrigger className="h-8 w-14 text-sm font-mono">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {ARITH_OPS.map((op) => (
                  <SelectItem key={op.value} value={op.value} className="font-mono text-sm">
                    {op.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <OperandPicker
              operand={condition.leftExtra ?? { kind: "field", value: "" }}
              fields={fields}
              onChange={(operand) => onChange({ leftExtra: operand })}
              allowLiteral={false}
              placeholder={t("pickField")}
            />
          </div>
        ) : null}
      </div>

      <div className="flex flex-col gap-1">
        <span className="text-[9px] uppercase tracking-wider font-semibold text-on-surface-variant">
          {t("operator")}
        </span>
        <Select
          value={condition.operator}
          onValueChange={(value) => {
            const operator = value as ComparisonOp;
            const patch: Partial<RuleCondition> = { operator };
            if (NO_RIGHT.includes(operator)) patch.right = undefined;
            else if (!condition.right) patch.right = { kind: "literal", value: "" };
            onChange(patch);
          }}
        >
          <SelectTrigger className="h-8 w-44 text-xs">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectGroup>
              <SelectLabel className="text-[10px]">{t("comparison")}</SelectLabel>
              {comparisonOps.filter((op) => !op.noRight).map((op) => (
                <SelectItem key={op.value} value={op.value} className="text-xs font-mono">
                  {op.label}
                </SelectItem>
              ))}
            </SelectGroup>
            <SelectGroup>
              <SelectLabel className="text-[10px]">{t("existence")}</SelectLabel>
              {comparisonOps.filter((op) => op.noRight).map((op) => (
                <SelectItem key={op.value} value={op.value} className="text-xs">
                  {op.label}
                </SelectItem>
              ))}
            </SelectGroup>
          </SelectContent>
        </Select>
      </div>

      {!noRight ? (
        <div className="flex flex-col gap-1">
          <span className="text-[9px] uppercase tracking-wider font-semibold text-on-surface-variant">
            {t("right")}
          </span>
          <OperandPicker
            operand={condition.right ?? { kind: "literal", value: "" }}
            fields={fields}
            onChange={(operand) => onChange({ right: operand })}
            placeholder={t("pickFieldOrValue")}
            literalInputKind={literalInputKind}
          />
        </div>
      ) : null}

      {canRemove ? (
        <div className="flex flex-col gap-1">
          <span className="text-[9px] uppercase tracking-wider text-transparent select-none">
            {"_"}
          </span>
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8 opacity-0 group-hover:opacity-100 text-outline hover:text-danger"
            onClick={onRemove}
            aria-label={tCommon("remove")}
          >
            <Trash2 className="h-3.5 w-3.5" />
          </Button>
        </div>
      ) : null}
    </div>
  );
}
