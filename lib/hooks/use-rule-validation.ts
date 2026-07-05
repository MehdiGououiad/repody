"use client";

import { useEffect, useState } from "react";
import type { DocumentDef, WorkflowRule } from "@/lib/types";
import { issuesByRuleId, validateRulesViaApi } from "@/lib/rules/rule-preview";

const DEBOUNCE_MS = 400;

/** Debounced backend rule validation for builder UI feedback. */
export function useRuleValidationIssues(
  documents: DocumentDef[],
  rules: WorkflowRule[]
): Record<string, string[]> {
  const [issuesMap, setIssuesMap] = useState<Record<string, string[]>>({});

  useEffect(() => {
    if (rules.length === 0) {
      setIssuesMap({});
      return;
    }

    let cancelled = false;
    const timer = window.setTimeout(() => {
      void validateRulesViaApi(documents, rules)
        .then((results) => {
          if (!cancelled) setIssuesMap(issuesByRuleId(results));
        })
        .catch(() => {
          if (!cancelled) setIssuesMap({});
        });
    }, DEBOUNCE_MS);

    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [documents, rules]);

  return issuesMap;
}
