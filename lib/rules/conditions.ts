import type {
  Aggregate,
  Arithmetic,
  ConditionExpression,
  FieldRef,
  LiteralValue,
  RuleCondition,
} from "@/lib/types";

export const fieldRef = (field = ""): FieldRef => ({ kind: "field", field });
export const literal = (value = ""): LiteralValue => ({ kind: "literal", value });

export function arithmetic(left = ""): Arithmetic {
  return { kind: "arithmetic", op: "+", left: fieldRef(left), right: fieldRef() };
}

export function aggregate(table = ""): Aggregate {
  return {
    kind: "aggregate",
    fn: "sum_rows",
    table,
    column: "",
    filterColumn: "",
    filterContains: "",
  };
}

/** Field names a condition reads (as the API's `condition_fields`). */
export function conditionFields(condition: RuleCondition): string[] {
  const left: ConditionExpression = condition.left;
  const names =
    left.kind === "field"
      ? [left.field]
      : left.kind === "arithmetic"
        ? [left.left.field, left.right.field]
        : [left.table];
  if (condition.right?.kind === "field") names.push(condition.right.field);
  return [...new Set(names.filter((name) => name.trim()))];
}

/** Whether every part of the condition is chosen: the fields it reads and, unless it only
 * checks presence, the value or field it is compared with. */
export function isComplete(condition: RuleCondition): boolean {
  const left = condition.left;
  const leftDone =
    left.kind === "field"
      ? Boolean(left.field.trim())
      : left.kind === "arithmetic"
        ? Boolean(left.left.field.trim() && left.right.field.trim())
        : Boolean(left.table.trim());
  const right = condition.right;
  const rightDone =
    !right ||
    (right.kind === "literal" ? Boolean(right.value.trim()) : Boolean(right.field.trim()));
  return leftDone && rightDone;
}

/** Whether the user has started filling the condition (for the "incomplete" hint). */
export function isTouched(condition: RuleCondition): boolean {
  return (
    conditionFields(condition).length > 0 ||
    (condition.right?.kind === "literal" && Boolean(condition.right.value.trim()))
  );
}
