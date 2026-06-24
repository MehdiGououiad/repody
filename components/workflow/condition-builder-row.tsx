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
  COMPARISON_OP_DEFS,
  NO_RIGHT,
  type ConditionFieldOption,
} from "@/components/workflow/condition-builder-model";
import { cn } from "@/lib/utils";
import type { ArithmeticOp, ComparisonOp, ConditionOperand, RuleCondition } from "@/lib/types";

function OperandPicker({
  operand,
  fields,
  onChange,
  placeholder,
  allowLiteral = true,
}: {
  operand: ConditionOperand;
  fields: ConditionFieldOption[];
  onChange: (operand: ConditionOperand) => void;
  placeholder?: string;
  allowLiteral?: boolean;
}) {
  const t = useTranslations("workflows.builder.rules.conditions");

  if (operand.kind === "literal") {
    return (
      <div className="flex items-center gap-1">
        <Input
          value={operand.value}
          onChange={(event) => onChange({ kind: "literal", value: event.target.value })}
          placeholder={t("literalPlaceholder")}
          className="h-8 text-xs w-32 font-mono"
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
  onChange,
  onRemove,
  canRemove,
}: {
  condition: RuleCondition;
  fields: ConditionFieldOption[];
  onChange: (patch: Partial<RuleCondition>) => void;
  onRemove: () => void;
  canRemove: boolean;
}) {
  const t = useTranslations("workflows.builder.rules.conditions");
  const tCommon = useTranslations("common");
  const hasArith = Boolean(condition.arithmeticOp);
  const noRight = NO_RIGHT.includes(condition.operator);
  const comparisonOps = COMPARISON_OP_DEFS.map((definition) => ({
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

  return (
    <div className="flex flex-wrap items-start gap-2 p-3 rounded-lg bg-surface-container-low border border-border group">
      <div className="flex flex-col gap-1">
        <span className="text-[9px] uppercase tracking-wider font-semibold text-on-surface-variant">
          {t("left")}
        </span>
        <div className="flex items-center gap-1">
          <OperandPicker
            operand={condition.left}
            fields={fields}
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
