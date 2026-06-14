import type { ConditionJunction, WorkflowRule } from "@/lib/types";
import { conditionsToExpression } from "@/lib/rules/expression";

/** Ensure logic rules have a compiled `body` from visual conditions before save/run. */
export function syncRuleBodies(rules: WorkflowRule[]): WorkflowRule[] {
  return rules.map((rule) => {
    if (rule.kind === "llm") return rule;
    const conditions = rule.conditions ?? [];
    if (!conditions.length) return rule;
    const body = conditionsToExpression(
      conditions,
      (rule.conditionJunction ?? "AND") as ConditionJunction
    );
    return { ...rule, body };
  });
}
