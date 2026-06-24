import type { RuleCondition, WorkflowRule } from "@/lib/types";
import { formatApiError as parseApiError } from "@/lib/api/api-error";
import { conditionsToExpression } from "@/lib/rules/expression";

const NO_RIGHT = new Set(["EXISTS", "IS_EMPTY"]);
const FIELD_REFERENCE =
  /(?<![\w@])@([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*)/g;

function conditionIncomplete(c: RuleCondition): boolean {
  if (!c.left?.value?.trim()) return true;
  if (NO_RIGHT.has(c.operator)) return false;
  return !c.right?.value?.trim();
}

/** Client-side checks before save — mirrors backend validation messages. */
export function getLogicRuleIssues(rule: WorkflowRule): string[] {
  const conditions = rule.conditions ?? [];
  if (!conditions.length) {
    return ["Add at least one condition."];
  }
  const incomplete = conditions.filter(conditionIncomplete);
  if (incomplete.length) {
    return ["Complete every condition (field, operator, and value)."];
  }
  const expression = conditionsToExpression(
    conditions,
    rule.conditionJunction ?? "AND"
  );
  if (!expression) {
    return ["Could not build an expression from these conditions."];
  }
  if (/\b(AND|OR)\b/.test(expression)) {
    return ["Expression uses invalid AND/OR — save again to recompile."];
  }
  return [];
}

export function getLlmFieldReferences(body: string): string[] {
  return Array.from(body.matchAll(FIELD_REFERENCE), (match) => match[1]).filter(
    (field, index, fields) => fields.indexOf(field) === index
  );
}

export function getRuleIssues(
  rule: WorkflowRule,
  availableFields?: string[]
): string[] {
  if (rule.kind === "llm") {
    const body = (rule.body || "").trim();
    if (!body) return ["LLM prompt is empty."];
    if (availableFields) {
      const available = new Set(availableFields);
      const unknown = getLlmFieldReferences(body).filter(
        (field) => !available.has(field)
      );
      if (unknown.length) {
        return [
          `Unknown field reference${unknown.length > 1 ? "s" : ""}: ${unknown
            .map((field) => `@${field}`)
            .join(", ")}.`,
        ];
      }
    }
    return [];
  }
  return getLogicRuleIssues(rule);
}

export function formatApiError(text: string): string {
  return parseApiError(text);
}
