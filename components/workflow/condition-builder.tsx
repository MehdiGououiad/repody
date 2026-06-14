"use client";

import { useTranslations } from "next-intl";
import { Plus, Trash2, Code2 } from "lucide-react";
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
import { cn, shortId } from "@/lib/utils";
import { conditionsToExpression, conditionToString } from "@/lib/rules/expression";
import type {
  ArithmeticOp,
  ComparisonOp,
  ConditionJunction,
  ConditionOperand,
  RuleCondition,
} from "@/lib/types";

// ── Constants ─────────────────────────────────────────────────────────────────

// Labels are resolved inside components via useTranslations — keep only value + noRight here
const COMPARISON_OP_DEFS: { value: ComparisonOp; key: string; noRight?: true }[] = [
  { value: "==",       key: "opEquals" },
  { value: "!=",       key: "opNotEquals" },
  { value: ">",        key: "opGt" },
  { value: ">=",       key: "opGte" },
  { value: "<",        key: "opLt" },
  { value: "<=",       key: "opLte" },
  { value: "IN",       key: "opIn" },
  { value: "NOT_IN",   key: "opNotIn" },
  { value: "EXISTS",   key: "opExists",  noRight: true },
  { value: "IS_EMPTY", key: "opIsEmpty", noRight: true },
];

const ARITH_OPS: { value: ArithmeticOp; label: string }[] = [
  { value: "+", label: "+" },
  { value: "-", label: "−" },
  { value: "*", label: "×" },
  { value: "/", label: "÷" },
];

const NO_RIGHT: ComparisonOp[] = ["EXISTS", "IS_EMPTY"];

export { conditionToString, conditionsToExpression, fieldToken } from "@/lib/rules/expression";

function newCondition(): RuleCondition {
  return {
    id: shortId(),
    left: { kind: "field", value: "" },
    operator: "==",
    right: { kind: "literal", value: "" },
  };
}

// ── Sub-components ────────────────────────────────────────────────────────────

/** Picker that shows schema field names as options, with a "literal value" fallback. */
function OperandPicker({
  operand,
  fields,
  onChange,
  placeholder,
  allowLiteral = true,
}: {
  operand: ConditionOperand;
  fields: { label: string; token: string }[];
  onChange: (op: ConditionOperand) => void;
  placeholder?: string;
  allowLiteral?: boolean;
}) {
  const t = useTranslations("workflows.builder.rules.conditions");

  if (operand.kind === "literal") {
    return (
      <div className="flex items-center gap-1">
        <Input
          value={operand.value}
          onChange={(e) => onChange({ kind: "literal", value: e.target.value })}
          placeholder={t("literalPlaceholder")}
          className="h-8 text-xs w-32 font-mono"
        />
        {fields.length > 0 && (
          <Button
            variant="ghost"
            size="sm"
            className="h-8 text-[10px] text-on-surface-variant px-2"
            onClick={() => onChange({ kind: "field", value: fields[0]?.token ?? "" })}
          >
            {t("switchToField")}
          </Button>
        )}
      </div>
    );
  }

  return (
    <div className="flex items-center gap-1">
      <Select
        value={operand.value}
        onValueChange={(v) => onChange({ kind: "field", value: v })}
      >
        <SelectTrigger className="h-8 text-xs w-40 font-mono">
          <SelectValue placeholder={placeholder ?? t("pickField")} />
        </SelectTrigger>
        <SelectContent>
          {fields.map((f) => (
            <SelectItem key={f.token} value={f.token} className="text-xs font-mono">
              {f.label}
            </SelectItem>
          ))}
          {fields.length === 0 && (
            <div className="px-3 py-2 text-xs text-on-surface-variant italic">
              {t("noFields")}
            </div>
          )}
        </SelectContent>
      </Select>
      {allowLiteral && (
        <Button
          variant="ghost"
          size="sm"
          className="h-8 text-[10px] text-on-surface-variant px-2"
          onClick={() => onChange({ kind: "literal", value: "" })}
        >
          {t("switchToValue")}
        </Button>
      )}
    </div>
  );
}

/** One condition row. */
function ConditionRow({
  condition,
  fields,
  onChange,
  onRemove,
  canRemove,
}: {
  condition: RuleCondition;
  fields: { label: string; token: string }[];
  onChange: (patch: Partial<RuleCondition>) => void;
  onRemove: () => void;
  canRemove: boolean;
}) {
  const t = useTranslations("workflows.builder.rules.conditions");
  const tCommon = useTranslations("common");
  const hasArith = !!condition.arithmeticOp;
  const noRight = NO_RIGHT.includes(condition.operator);

  // Resolved operator options with translated labels
  const COMPARISON_OPS = COMPARISON_OP_DEFS.map((d) => ({
    value: d.value,
    label: t(d.key as Parameters<typeof t>[0]),
    noRight: d.noRight,
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
      {/* LEFT operand */}
      <div className="flex flex-col gap-1">
        <span className="text-[9px] uppercase tracking-wider font-semibold text-on-surface-variant">
          {t("left")}
        </span>
        <div className="flex items-center gap-1">
          <OperandPicker
            operand={condition.left}
            fields={fields}
            onChange={(op) => onChange({ left: op })}
            allowLiteral={false}
            placeholder={t("pickField")}
          />

          {/* Arithmetic toggle */}
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

        {/* Arithmetic second operand */}
        {hasArith && (
          <div className="flex items-center gap-1 pl-1">
            <Select
              value={condition.arithmeticOp ?? "+"}
              onValueChange={(v) => onChange({ arithmeticOp: v as ArithmeticOp })}
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
              onChange={(op) => onChange({ leftExtra: op })}
              allowLiteral={false}
              placeholder={t("pickField")}
            />
          </div>
        )}
      </div>

      {/* OPERATOR */}
      <div className="flex flex-col gap-1">
        <span className="text-[9px] uppercase tracking-wider font-semibold text-on-surface-variant">
          {t("operator")}
        </span>
        <Select
          value={condition.operator}
          onValueChange={(v) => {
            const op = v as ComparisonOp;
            const patch: Partial<RuleCondition> = { operator: op };
            if (NO_RIGHT.includes(op)) patch.right = undefined;
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
              {COMPARISON_OPS.filter((o) => !o.noRight).map((op) => (
                <SelectItem key={op.value} value={op.value} className="text-xs font-mono">
                  {op.label}
                </SelectItem>
              ))}
            </SelectGroup>
            <SelectGroup>
              <SelectLabel className="text-[10px]">{t("existence")}</SelectLabel>
              {COMPARISON_OPS.filter((o) => o.noRight).map((op) => (
                <SelectItem key={op.value} value={op.value} className="text-xs">
                  {op.label}
                </SelectItem>
              ))}
            </SelectGroup>
          </SelectContent>
        </Select>
      </div>

      {/* RIGHT operand */}
      {!noRight && (
        <div className="flex flex-col gap-1">
          <span className="text-[9px] uppercase tracking-wider font-semibold text-on-surface-variant">
            {t("right")}
          </span>
          <OperandPicker
            operand={condition.right ?? { kind: "literal", value: "" }}
            fields={fields}
            onChange={(op) => onChange({ right: op })}
            placeholder={t("pickFieldOrValue")}
          />
        </div>
      )}

      {/* Remove */}
      {canRemove && (
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
      )}
    </div>
  );
}

// ── Main export ───────────────────────────────────────────────────────────────

export function ConditionBuilder({
  conditions,
  junction,
  fields,
  onConditionsChange,
  onJunctionChange,
}: {
  conditions: RuleCondition[];
  junction: ConditionJunction;
  fields: { label: string; token: string }[];
  onConditionsChange: (c: RuleCondition[]) => void;
  onJunctionChange: (j: ConditionJunction) => void;
}) {
  const t = useTranslations("workflows.builder.rules.conditions");

  const update = (id: string, patch: Partial<RuleCondition>) =>
    onConditionsChange(conditions.map((c) => (c.id === id ? { ...c, ...patch } : c)));

  const remove = (id: string) =>
    onConditionsChange(conditions.filter((c) => c.id !== id));

  const add = () => onConditionsChange([...conditions, newCondition()]);

  const expression = conditionsToExpression(conditions, junction);

  return (
    <div className="space-y-2">
      {/* Conditions */}
      {conditions.map((cond, idx) => (
        <div key={cond.id}>
          <ConditionRow
            condition={cond}
            fields={fields}
            onChange={(patch) => update(cond.id, patch)}
            onRemove={() => remove(cond.id)}
            canRemove={conditions.length > 1}
          />
          {/* Junction connector between rows */}
          {idx < conditions.length - 1 && (
            <div className="flex items-center gap-2 py-1 pl-3">
              <div className="h-px flex-1 bg-border" />
              <span className="text-[10px] font-semibold uppercase tracking-wide text-on-surface-variant px-2">
                {t("alsoCheck")}
              </span>
              <div className="h-px flex-1 bg-border" />
            </div>
          )}
        </div>
      ))}

      {/* Add condition */}
      <Button variant="outline" size="sm" className="w-full h-8 text-xs" onClick={add}>
        <Plus className="h-3.5 w-3.5" />
        {t("addCondition")}
      </Button>

      {/* Expression preview — one check per condition */}
      <div className="space-y-1">
        {conditions.some((c) => conditionToString(c)) ? (
          <div className="rounded-lg border border-border bg-surface-container-lowest px-3 py-2 space-y-1.5">
            <p className="text-[10px] text-on-surface-variant">{t("separateChecksHint")}</p>
            {conditions.map((cond, idx) => {
              const line = conditionToString(cond);
              if (!line) return null;
              return (
                <div key={cond.id} className="flex items-start gap-2">
                  <Code2 className="h-3.5 w-3.5 text-on-surface-variant mt-0.5 shrink-0" />
                  <code className="text-[11px] font-mono text-on-surface-variant break-all">
                    {t("checkN", { n: idx + 1 })}: {line}
                  </code>
                </div>
              );
            })}
          </div>
        ) : conditions.some((c) => c.left?.value || c.right?.value) ? (
          <p className="text-[11px] text-danger rounded-lg border border-danger/30 bg-danger/5 px-3 py-2">
            {t("expressionIncomplete")}
          </p>
        ) : null}
      </div>
    </div>
  );
}
