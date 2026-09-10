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
import type { ConditionFieldOption } from "@/components/workflow/condition-builder-model";
import {
  LiteralValueInput,
  literalPlaceholderForKind,
} from "@/components/workflow/condition-literal-value-input";
import type { LiteralInputKind } from "@/lib/rules/condition-input-kind";
import type { ConditionOperand } from "@/lib/types";

export function OperandPicker({
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
      <Select value={operand.value} onValueChange={(value) => onChange({ kind: "field", value })}>
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
            <div className="px-3 py-2 text-xs text-on-surface-variant italic">{t("noFields")}</div>
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
