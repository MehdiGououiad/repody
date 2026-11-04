import type { ArithmeticOp, ComparisonOp } from "@/lib/types";

/** Comparison operators shown in the Logic-rule condition builder. */
export const COMPARISON_OP_DEFS: { value: ComparisonOp; key: string; noRight?: true }[] = [
  { value: "==", key: "opEquals" },
  { value: "!=", key: "opNotEquals" },
  { value: ">", key: "opGt" },
  { value: ">=", key: "opGte" },
  { value: "<", key: "opLt" },
  { value: "<=", key: "opLte" },
  { value: "IN", key: "opIn" },
  { value: "NOT_IN", key: "opNotIn" },
  { value: "EXISTS", key: "opExists", noRight: true },
  { value: "IS_EMPTY", key: "opIsEmpty", noRight: true },
];

export const ARITH_OPS: { value: ArithmeticOp; label: string }[] = [
  { value: "+", label: "+" },
  { value: "-", label: "-" },
  { value: "*", label: "x" },
  { value: "/", label: "/" },
];

/** Operators that test the left side alone (no right-hand operand). */
export const NO_RIGHT = new Set<ComparisonOp>(
  COMPARISON_OP_DEFS.filter((op) => op.noRight).map((op) => op.value)
);
