import type { Catalog, ComparisonOp } from "@/lib/types";

/** Comparison operators, in the order the builder offers them, with their message keys. */
export const COMPARISON_OPS = [
  { value: "==", key: "opEquals" },
  { value: "!=", key: "opNotEquals" },
  { value: ">", key: "opGt" },
  { value: ">=", key: "opGte" },
  { value: "<", key: "opLt" },
  { value: "<=", key: "opLte" },
  { value: "IN", key: "opIn" },
  { value: "NOT_IN", key: "opNotIn" },
  { value: "EXISTS", key: "opExists" },
  { value: "IS_EMPTY", key: "opIsEmpty" },
] as const satisfies readonly { value: ComparisonOp; key: string }[];

/** Operators that fit a left side of `type`, as the API serves them (`GET /v1/catalog`, the
 * same rule it applies on save); a type it does not list (`region:FR`) takes the default's. */
export function operatorsFor(type: string | undefined, catalog: Catalog) {
  if (!type) return [...COMPARISON_OPS];
  const allowed =
    catalog.operatorsByType[type] ?? catalog.operatorsByType[catalog.defaultType] ?? [];
  return COMPARISON_OPS.filter(({ value }) => allowed.includes(value));
}

/** Whether the operator tests the left side alone (no right-hand operand). */
export function isPresenceOp(operator: ComparisonOp, catalog: Catalog): boolean {
  return catalog.presenceOperators.includes(operator);
}

export type LiteralInputKind = "text" | "date" | "datetime-local" | "time" | "number" | "boolean";

/** The input that fits a literal compared with a value of `type`. */
export function literalInputKind(type: string | undefined, catalog: Catalog): LiteralInputKind {
  if (type && catalog.numberTypes.includes(type)) return "number";
  switch (type) {
    case "date":
      return "date";
    case "date-time":
      return "datetime-local";
    case "time":
      return "time";
    case "boolean":
      return "boolean";
    default:
      return "text";
  }
}
