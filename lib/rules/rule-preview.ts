import { browserApi, unwrap } from "@/lib/api/openapi-client";
import type { DocumentDef, WorkflowRule } from "@/lib/types";

export type RuleValidationResult = {
  ruleId: string;
  issues: string[];
};

/** Authoritative rule validation - backend compiler is the source of truth. */
export async function validateRulesViaApi(
  documents: DocumentDef[],
  rules: WorkflowRule[]
): Promise<RuleValidationResult[]> {
  const data = await unwrap(
    browserApi.POST("/v1/workflows/validate-rules", {
      body: { documents, rules } as never,
      signal: AbortSignal.timeout(30_000),
    })
  );
  return data.rules;
}

export function issuesByRuleId(results: RuleValidationResult[]): Record<string, string[]> {
  return Object.fromEntries(results.map((row) => [row.ruleId, row.issues]));
}

export function firstRuleIssue(
  results: RuleValidationResult[],
  rules: WorkflowRule[]
): string | null {
  for (const rule of rules) {
    const issues = results.find((row) => row.ruleId === rule.id)?.issues ?? [];
    if (issues.length) {
      const label = rule.name?.trim() || rule.id;
      return `${label}: ${issues[0]}`;
    }
  }
  return null;
}
