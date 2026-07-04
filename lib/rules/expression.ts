import type { ComparisonOp, ConditionJunction, ConditionOperand, RuleCondition } from "@/lib/types";

const NO_RIGHT: ComparisonOp[] = ["EXISTS", "IS_EMPTY"];

export function fieldToken(name: string): string {
  return name.trim().toLowerCase().replace(/\s+/g, "_");
}

function fieldRef(token: string): string | null {
  const t = token.trim();
  if (!t) return null;
  if (/^[A-Za-z_][A-Za-z0-9_]*$/.test(t)) return t;
  if (t.includes(".")) {
    const parts = t.split(".").map((part) => fieldToken(part));
    if (parts.every((part) => /^[a-z_][a-z0-9_]*$/.test(part))) {
      return parts.length > 1 ? parts.join("__") : parts[0]!;
    }
  }
  const normalized = fieldToken(t);
  return /^[a-z_][a-z0-9_]*$/.test(normalized) ? normalized : null;
}

function literalToPy(value: string): string | null {
  const v = value.trim();
  if (!v) return null;
  const num = Number(v);
  if (!Number.isNaN(num) && v !== "") return String(num);
  return JSON.stringify(v);
}

function operandToPy(op: ConditionOperand): string | null {
  if (op.kind === "literal") return literalToPy(op.value);
  return fieldRef(op.value);
}

function listLiteralToPy(value: string): string | null {
  const parts = value
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
  if (!parts.length) return null;
  const items = parts.map((p) => literalToPy(p)).filter((x): x is string => x !== null);
  if (items.length !== parts.length) return null;
  return `[${items.join(", ")}]`;
}

export function conditionToString(c: RuleCondition): string {
  const leftBase = operandToPy(c.left);
  if (!leftBase) return "";

  let left = leftBase;
  if (c.arithmeticOp && c.leftExtra) {
    const extra = operandToPy(c.leftExtra);
    if (!extra) return "";
    left = `(${leftBase} ${c.arithmeticOp} ${extra})`;
  }

  if (NO_RIGHT.includes(c.operator)) {
    if (c.operator === "EXISTS") {
      return `(${left} is not None and str(${left}).strip() not in ("", "—"))`;
    }
    return `(${left} is None or str(${left}).strip() in ("", "—"))`;
  }

  if (!c.right) return "";

  if (c.operator === "IN" || c.operator === "NOT_IN") {
    const joiner = c.operator === "IN" ? "in" : "not in";
    if (c.right.kind === "literal" && c.right.value.includes(",")) {
      const list = listLiteralToPy(c.right.value);
      if (!list) return "";
      return `${left} ${joiner} ${list}`;
    }
    const right = operandToPy(c.right);
    if (!right) return "";
    return `${left} ${joiner} ${right}`;
  }

  const right = operandToPy(c.right);
  if (!right) return "";
  return `${left} ${c.operator} ${right}`;
}

export function conditionsToExpression(
  conditions: RuleCondition[],
  junction: ConditionJunction
): string {
  const parts = conditions.map(conditionToString).filter(Boolean);
  if (!parts.length) return "";
  if (parts.length === 1) return parts[0]!;
  const pyJunction = junction === "OR" ? "or" : "and";
  return `(${parts.join(`) ${pyJunction} (`)})`;
}
