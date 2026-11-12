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
  // An unqualified name (`total`) still matches its qualified option (`Invoice.total`): the
  // API reads both, and a rule written before a second document was added keeps working.
  const match =
    options.find((option) => option.name === value) ??
    options.find((option) => option.name.endsWith(`.${value}`));
  const stale = value && !match;
  return (
    <Select value={match?.name ?? value} onValueChange={onChange}>
      <SelectTrigger
        className={cn(
          "w-40 font-mono text-xs",
          stale && "text-fail-ink shadow-[inset_0_0_0_1px_var(--fail)]",
          className
        )}
      >
        <SelectValue placeholder={placeholder} />
      </SelectTrigger>
      <SelectContent>
        {stale ? (
          <SelectItem value={value} className="font-mono text-xs text-fail-ink">
            {value}
          </SelectItem>
        ) : null}
        {options.map((option) => (
          <SelectItem key={option.name} value={option.name} className="font-mono text-xs">
            {option.name}
            <span className="ms-auto ps-3 font-sans text-xs text-ink-4">{option.type}</span>
          </SelectItem>
        ))}
        {options.length === 0 ? (
          <div className="px-2 py-1.5 text-sm text-ink-3">{t("noFields")}</div>
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
    <Button variant="ghost" size="sm" className="text-ink-3" onClick={() => onChange(next)}>
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
