"use client";

import { useTranslations } from "next-intl";
import { ToggleGroup } from "radix-ui";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { FieldRefPicker, FieldSelect } from "@/components/workflow/rules/condition-operand-picker";
import { aggregate, arithmetic, fieldRef } from "@/lib/rules/conditions";
import type { FieldOption, TableOption } from "@/lib/rules/document-fields";
import type {
  Aggregate,
  AggregateFn,
  ArithmeticOp,
  Catalog,
  ConditionExpression,
} from "@/lib/types";
import { cn } from "@/lib/utils";

const KINDS = ["field", "arithmetic", "aggregate"] as const;
const ARITHMETIC_OPS: { value: ArithmeticOp; label: string }[] = [
  { value: "+", label: "+" },
  { value: "-", label: "−" },
  { value: "*", label: "×" },
  { value: "/", label: "÷" },
];
const AGGREGATES = [
  { value: "sum_rows", key: "aggSumRows" },
  { value: "sum_rows_where", key: "aggSumRowsWhere" },
  { value: "count_rows_where", key: "aggCountRowsWhere" },
] as const satisfies readonly { value: AggregateFn; key: string }[];

/** Switch the left side's kind, keeping the field already chosen where it still fits. */
function switchKind(
  left: ConditionExpression,
  kind: ConditionExpression["kind"],
  tables: TableOption[]
) {
  const field =
    left.kind === "field" ? left.field : left.kind === "arithmetic" ? left.left.field : "";
  if (kind === "field") return fieldRef(field);
  if (kind === "arithmetic") return arithmetic(field);
  return aggregate(tables[0]?.name);
}

function AggregateEditor({
  value,
  tables,
  onChange,
}: {
  value: Aggregate;
  tables: TableOption[];
  onChange: (value: Aggregate) => void;
}) {
  const t = useTranslations("workflows.builder.rules.conditions");
  const columns = tables.find((table) => table.name === value.table)?.columns ?? [];
  const patch = (next: Partial<Aggregate>) => onChange({ ...value, ...next });

  return (
    <div className="flex flex-wrap items-center gap-1">
      <Select value={value.fn} onValueChange={(fn) => patch({ fn: fn as AggregateFn })}>
        <SelectTrigger className="h-8 w-36 text-xs">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {AGGREGATES.map((option) => (
            <SelectItem key={option.value} value={option.value} className="text-xs">
              {t(option.key)}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      <FieldSelect
        value={value.table}
        options={tables.map((table) => ({ name: table.name, type: "object-array" }))}
        onChange={(table) => patch({ table, column: "", filterColumn: "" })}
        placeholder={t("pickTable")}
      />
      {value.fn !== "count_rows_where" ? (
        <FieldSelect
          value={value.column}
          options={columns}
          onChange={(column) => patch({ column })}
          placeholder={t("amountColumn")}
          className="w-32"
        />
      ) : null}
      {value.fn !== "sum_rows" ? (
        <>
          <FieldSelect
            value={value.filterColumn}
            options={columns}
            onChange={(filterColumn) => patch({ filterColumn })}
            placeholder={t("filterColumn")}
            className="w-32"
          />
          <Input
            value={value.filterContains}
            onChange={(event) => patch({ filterContains: event.target.value })}
            placeholder={t("filterContains")}
            className="h-8 w-44 text-xs font-mono"
          />
        </>
      ) : null}
    </div>
  );
}

/** The left side of a condition: a field, arithmetic on two number fields, or a table aggregate. */
export function ConditionLeft({
  value,
  fields,
  tables,
  catalog,
  onChange,
}: {
  value: ConditionExpression;
  fields: FieldOption[];
  tables: TableOption[];
  catalog: Catalog;
  onChange: (value: ConditionExpression) => void;
}) {
  const t = useTranslations("workflows.builder.rules.conditions");
  const scalars = fields.filter((field) => field.type !== catalog.tableType);
  const numbers = fields.filter((field) => catalog.numberTypes.includes(field.type));
  const available = KINDS.filter(
    (kind) =>
      kind === "field" ||
      kind === value.kind ||
      (kind === "arithmetic" ? numbers.length > 0 : tables.length > 0)
  );

  return (
    <div className="flex flex-wrap items-center gap-1">
      {available.length > 1 ? (
        <ToggleGroup.Root
          type="single"
          value={value.kind}
          onValueChange={(kind) =>
            kind && onChange(switchKind(value, kind as ConditionExpression["kind"], tables))
          }
          className="inline-flex rounded border border-line p-0.5"
          aria-label={t("left")}
        >
          {available.map((kind) => (
            <ToggleGroup.Item
              key={kind}
              value={kind}
              className={cn(
                "h-7 px-2 rounded text-2xs font-semibold  ",
                "text-ink-3 hover:text-ink",
                "data-[state=on]:bg-accent/10 data-[state=on]:text-ink"
              )}
            >
              {t(`kinds.${kind}`)}
            </ToggleGroup.Item>
          ))}
        </ToggleGroup.Root>
      ) : null}
      {value.kind === "field" ? (
        <FieldRefPicker value={value} fields={scalars} onChange={onChange} />
      ) : null}
      {value.kind === "arithmetic" ? (
        <>
          <FieldRefPicker
            value={value.left}
            fields={numbers}
            onChange={(left) => onChange({ ...value, left })}
          />
          <Select
            value={value.op}
            onValueChange={(op) => onChange({ ...value, op: op as ArithmeticOp })}
          >
            <SelectTrigger className="h-8 w-14 text-sm font-mono" aria-label={t("arithmeticOp")}>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {ARITHMETIC_OPS.map((op) => (
                <SelectItem key={op.value} value={op.value} className="font-mono text-sm">
                  {op.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <FieldRefPicker
            value={value.right}
            fields={numbers}
            onChange={(right) => onChange({ ...value, right })}
          />
        </>
      ) : null}
      {value.kind === "aggregate" ? (
        <AggregateEditor value={value} tables={tables} onChange={onChange} />
      ) : null}
    </div>
  );
}
