import { browserApi, unwrap } from "@/lib/api/openapi-client";
import type { Schema } from "@/lib/api/schema-types";
import type { DocumentDef, WorkflowRule } from "@/lib/types";

/** Backend feedback on one rule: what blocks saving, and each condition as text. */
export type RuleValidationResult = Schema["RuleCheck"];

export async function validateRulesViaApi(
  documents: DocumentDef[],
  rules: WorkflowRule[]
): Promise<RuleValidationResult[]> {
  const data = await unwrap(
    browserApi.POST("/v1/workflows/check-rules", {
      body: { documents, rules },
      signal: AbortSignal.timeout(30_000),
    })
  );
  return data.rules;
}

export function resultsByRuleId(
  results: RuleValidationResult[]
): Record<string, RuleValidationResult> {
  return Object.fromEntries(results.map((row) => [row.ruleId, row]));
}

export function firstRuleIssue(results: RuleValidationResult[]): string | null {
  return results.flatMap((row) => row.issues)[0] ?? null;
}
