import { COMPARISON_OP_DEFS } from "@/components/workflow/condition-builder-model";
import { DEFAULT_NUEXTRACT_TEMPLATE_TYPE } from "@/lib/nuextract-types";
import type { ComparisonOp } from "@/lib/types";

export type LiteralInputKind = "text" | "date" | "datetime-local" | "time" | "number" | "boolean";

export const DATE_LIKE_TEMPLATE_TYPES = new Set(["date", "date-time", "time"]);

export type ConditionFieldMeta = {
  token: string;
  templateType?: string;
};

export function literalInputKindForTemplateType(templateType?: string): LiteralInputKind {
  switch (templateType) {
    case "date":
      return "date";
    case "date-time":
      return "datetime-local";
    case "time":
      return "time";
    case "integer":
      return "number";
    case "number":
    case "currency":
      return "number";
    case "boolean":
      return "boolean";
    default:
      return "text";
  }
}

export function resolveFieldTemplateType(
  token: string,
  fields: ConditionFieldMeta[]
): string | undefined {
  const trimmed = token.trim();
  if (!trimmed) return undefined;
  return fields.find((field) => field.token === trimmed)?.templateType;
}

export function comparisonOpsForTemplateType(templateType?: string) {
  if (templateType && DATE_LIKE_TEMPLATE_TYPES.has(templateType)) {
    return COMPARISON_OP_DEFS.filter(
      (op) => op.value !== "IN" && op.value !== "NOT_IN"
    );
  }
  return COMPARISON_OP_DEFS;
}

export function defaultTemplateTypeForField(fields: ConditionFieldMeta[]): string {
  return fields[0]?.templateType ?? DEFAULT_NUEXTRACT_TEMPLATE_TYPE;
}

export function isDateComparisonOperator(operator: ComparisonOp): boolean {
  return operator === "<" || operator === "<=" || operator === ">" || operator === ">=";
}
