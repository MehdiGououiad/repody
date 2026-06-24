import { shortId } from "@/lib/utils";
import type { ArithmeticOp, ComparisonOp, RuleCondition } from "@/lib/types";

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

export const NO_RIGHT: ComparisonOp[] = ["EXISTS", "IS_EMPTY"];

export type ConditionFieldOption = { label: string; token: string };

export function newCondition(): RuleCondition {
  return {
    id: shortId(),
    left: { kind: "field", value: "" },
    operator: "==",
    right: { kind: "literal", value: "" },
  };
}
