"use client";

import { useTranslations } from "next-intl";
import { SegmentedControl, SegmentedControlOption } from "@/components/ui/segmented-control";
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
  // An unqualified name (`total`) still matches its qualified option (`Invoice.total`): the
  // API reads both, and a rule written before a second document was added keeps working.
  const match =
    options.find((option) => option.name === value) ??
    options.find((option) => option.name.endsWith(`.${value}`));
  const stale = value && !match;
  return (
    <Select
      value={match?.name ?? value}
      onValueChange={(next: string | null) => next !== null && onChange(next)}
    >
      <SelectTrigger
        aria-label={placeholder}
        className={cn(
          "w-40 font-mono text-xs",
          stale && "text-fail-ink shadow-[inset_0_0_0_1px_var(--fail)]",
          className,
        )}
      >
        <SelectValue placeholder={placeholder} />
      </SelectTrigger>
      <SelectContent>
        {stale ? (
          <SelectItem value={value} label={value} className="font-mono text-xs text-fail-ink">
            {value}
          </SelectItem>
        ) : null}
        {options.map((option) => (
          <SelectItem
            key={option.name}
            value={option.name}
            label={option.name}
            className="font-mono text-xs"
          >
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

  return (
    <div className="flex flex-wrap items-center gap-1">
      {fields.length > 0 ? (
        <SegmentedControl
          aria-label={t("right")}
          value={operand.kind}
          onValueChange={(kind) => {
            if (kind === "literal") onChange(literal());
            else if (kind === "field") onChange(fieldRef(fields[0]?.name));
          }}
        >
          <SegmentedControlOption value="literal">{t("kinds.value")}</SegmentedControlOption>
          <SegmentedControlOption value="field">{t("kinds.field")}</SegmentedControlOption>
        </SegmentedControl>
      ) : null}
      {operand.kind === "literal" ? (
        <LiteralValueInput
          value={operand.value}
          onChange={(value) => onChange(literal(value))}
          inputKind={inputKind}
        />
      ) : (
        <FieldSelect
          value={operand.field}
          options={fields}
          onChange={(name) => onChange(fieldRef(name))}
          placeholder={t("pickFieldOrValue")}
        />
      )}
    </div>
  );
}
