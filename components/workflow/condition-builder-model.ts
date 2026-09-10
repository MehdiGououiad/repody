import { NO_RIGHT } from "@/lib/rules/comparison-ops";
import type { ArithmeticOp, RuleCondition } from "@/lib/types";
import { shortId } from "@/lib/utils";

export { NO_RIGHT };

export const ARITH_OPS: { value: ArithmeticOp; label: string }[] = [
  { value: "+", label: "+" },
  { value: "-", label: "-" },
  { value: "*", label: "x" },
  { value: "/", label: "/" },
];

export type ConditionFieldOption = {
  label: string;
  token: string;
  templateType?: string;
  tableParent?: string;
};

export function newCondition(): RuleCondition {
  return {
    id: shortId(),
    left: { kind: "field", value: "" },
    operator: "==",
    right: { kind: "literal", value: "" },
  };
}
