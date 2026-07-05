import type { DocumentDef, WorkflowRule } from "@/lib/types";
import { browserJson } from "@/lib/api/http";

export type RuleValidationResult = {
  ruleId: string;
  issues: string[];
};

type ValidateRulesResponse = {
  rules: Array<{ ruleId: string; issues: string[] }>;
};

/** Authoritative rule validation — backend compiler is the source of truth. */
export async function validateRulesViaApi(
  documents: DocumentDef[],
  rules: WorkflowRule[]
): Promise<RuleValidationResult[]> {
  const data = await browserJson<ValidateRulesResponse>("/v1/workflows/validate-rules", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ documents, rules }),
    timeoutMs: 30_000,
  });
  return data.rules.map((row) => ({
    ruleId: row.ruleId,
    issues: row.issues,
  }));
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
