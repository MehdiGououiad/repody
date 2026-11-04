import { COMPARISON_OP_DEFS } from "@/lib/rules/comparison-ops";

export type LiteralInputKind = "text" | "date" | "datetime-local" | "time" | "number" | "boolean";

export const DATE_LIKE_TEMPLATE_TYPES = new Set(["date", "date-time", "time"]);

export function literalInputKindForTemplateType(templateType?: string): LiteralInputKind {
  switch (templateType) {
    case "date":
      return "date";
    case "date-time":
      return "datetime-local";
    case "time":
      return "time";
    case "integer":
    case "number":
      return "number";
    case "boolean":
      return "boolean";
    default:
      return "text";
  }
}

export function resolveFieldTemplateType(
  token: string,
  fields: { token: string; templateType?: string }[]
): string | undefined {
  const trimmed = token.trim();
  if (!trimmed) return undefined;
  return fields.find((field) => field.token === trimmed)?.templateType;
}

/** Types the backend compares in order (numbers, ISO dates and times); the rest use == / IN. */
export const NUMBER_TEMPLATE_TYPES = new Set(["number", "integer"]);
const ORDERED_TEMPLATE_TYPES = new Set([...NUMBER_TEMPLATE_TYPES, ...DATE_LIKE_TEMPLATE_TYPES]);
const ORDERING_OPS = new Set(["<", "<=", ">", ">="]);

/** Operators that fit the left field's type (the backend rejects the others on save). */
export function comparisonOpsForTemplateType(templateType?: string) {
  return COMPARISON_OP_DEFS.filter((op) => {
    if (ORDERING_OPS.has(op.value))
      return !templateType || ORDERED_TEMPLATE_TYPES.has(templateType);
    if (op.value === "IN" || op.value === "NOT_IN") {
      return !templateType || !DATE_LIKE_TEMPLATE_TYPES.has(templateType);
    }
    return true;
  });
}
