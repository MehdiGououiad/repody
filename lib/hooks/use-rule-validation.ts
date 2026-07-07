"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type { DocumentDef, WorkflowRule } from "@/lib/types";
import { rulesValidationFingerprint } from "@/lib/workflow/draft-fingerprint";
import { issuesByRuleId, validateRulesViaApi } from "@/lib/rules/rule-preview";

const DEBOUNCE_MS = 400;

/** Debounced backend rule validation for builder UI feedback. */
export function useRuleValidationIssues(
  documents: DocumentDef[],
  rules: WorkflowRule[]
): Record<string, string[]> {
  const [issuesMap, setIssuesMap] = useState<Record<string, string[]>>({});
  const lastValidatedRef = useRef<string | null>(null);
  const fingerprint = useMemo(
    () => rulesValidationFingerprint(documents, rules),
    [documents, rules]
  );

  useEffect(() => {
    if (rules.length === 0) {
      lastValidatedRef.current = null;
      return;
    }

    if (fingerprint === lastValidatedRef.current) {
      return;
    }

    let cancelled = false;
    const timer = window.setTimeout(() => {
      void validateRulesViaApi(documents, rules)
        .then((results) => {
          if (!cancelled) {
            lastValidatedRef.current = fingerprint;
            setIssuesMap(issuesByRuleId(results));
          }
        })
        .catch(() => {
          if (!cancelled) setIssuesMap({});
        });
    }, DEBOUNCE_MS);

    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [documents, fingerprint, rules]);

  return rules.length === 0 ? {} : issuesMap;
}
