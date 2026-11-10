"use client";

import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { LiteralValueInput } from "@/components/workflow/rules/condition-literal-value-input";
import { fieldRef, literal } from "@/lib/rules/conditions";
import type { FieldOption } from "@/lib/rules/document-fields";
import type { LiteralInputKind } from "@/lib/rules/operators";
import type { ConditionOperand, FieldRef } from "@/lib/types";
import { cn } from "@/lib/utils";

/** A select of schema fields (or columns), showing each one's type. */
export function FieldSelect({
  value,
  options,
  onChange,
  placeholder,
  className,
}: {
  value: string;
  options: FieldOption[];
  onChange: (name: string) => void;
  placeholder: string;
  className?: string;
}) {
  const t = useTranslations("workflows.builder.rules.conditions");
  // A stored name that no longer fits (renamed field, changed type) still shows, so the rule's
  // check error points at something visible.
  const stale = value && !options.some((option) => option.name === value);
  return (
    <Select value={value} onValueChange={onChange}>
      <SelectTrigger
        className={cn(
          "h-8 text-xs w-40 font-mono",
          stale && "border-danger text-danger",
          className
        )}
      >
        <SelectValue placeholder={placeholder} />
      </SelectTrigger>
      <SelectContent>
        {stale ? (
          <SelectItem value={value} className="text-xs font-mono text-danger">
            {value}
          </SelectItem>
        ) : null}
        {options.map((option) => (
          <SelectItem key={option.name} value={option.name} className="text-xs font-mono">
            {option.name}
            <span className="ml-2 text-[10px] text-on-surface-variant">{option.type}</span>
          </SelectItem>
        ))}
        {options.length === 0 ? (
          <div className="px-3 py-2 text-xs text-on-surface-variant italic">{t("noFields")}</div>
        ) : null}
      </SelectContent>
    </Select>
  );
}

/** A field reference only (left sides and arithmetic operands). */
export function FieldRefPicker({
  value,
  fields,
  onChange,
}: {
  value: FieldRef;
  fields: FieldOption[];
  onChange: (value: FieldRef) => void;
}) {
  const t = useTranslations("workflows.builder.rules.conditions");
  return (
    <FieldSelect
      value={value.field}
      options={fields}
      onChange={(name) => onChange(fieldRef(name))}
      placeholder={t("pickField")}
    />
  );
}

/** The right side: a field, or a value typed by the user. */
export function OperandPicker({
  operand,
  fields,
  onChange,
  inputKind,
}: {
  operand: ConditionOperand;
  fields: FieldOption[];
  onChange: (operand: ConditionOperand) => void;
  inputKind: LiteralInputKind;
}) {
  const t = useTranslations("workflows.builder.rules.conditions");
  const switchButton = (label: string, next: ConditionOperand) => (
    <Button
      variant="ghost"
      size="sm"
      className="h-8 text-[10px] text-on-surface-variant px-2"
      onClick={() => onChange(next)}
    >
      {label}
    </Button>
  );

  if (operand.kind === "literal") {
    return (
      <div className="flex items-center gap-1">
        <LiteralValueInput
          value={operand.value}
          onChange={(value) => onChange(literal(value))}
          inputKind={inputKind}
        />
        {fields.length > 0 ? switchButton(t("switchToField"), fieldRef(fields[0]?.name)) : null}
      </div>
    );
  }
  return (
    <div className="flex items-center gap-1">
      <FieldSelect
        value={operand.field}
        options={fields}
        onChange={(name) => onChange(fieldRef(name))}
        placeholder={t("pickFieldOrValue")}
      />
      {switchButton(t("switchToValue"), literal())}
    </div>
  );
}
