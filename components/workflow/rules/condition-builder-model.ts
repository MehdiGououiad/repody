import { NO_RIGHT } from "@/lib/rules/comparison-ops";
import type { ArithmeticOp } from "@/lib/types";

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

export { newCondition } from "@/lib/workflow/new-items";
