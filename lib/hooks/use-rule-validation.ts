"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  type RuleValidationResult,
  resultsByRuleId,
  validateRulesViaApi,
} from "@/lib/rules/rule-preview";
import type { DocumentDef, WorkflowRule } from "@/lib/types";
import { rulesValidationFingerprint } from "@/lib/workflow/draft-fingerprint";

const DEBOUNCE_MS = 400;

/** Debounced backend rule validation (issues and compiled checks) for builder UI feedback. */
export function useRuleValidation(
  documents: DocumentDef[],
  rules: WorkflowRule[]
): Record<string, RuleValidationResult> {
  const [resultsMap, setResultsMap] = useState<Record<string, RuleValidationResult>>({});
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
            setResultsMap(resultsByRuleId(results));
          }
        })
        .catch(() => {
          if (!cancelled) setResultsMap({});
        });
    }, DEBOUNCE_MS);

    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [documents, fingerprint, rules]);

  return rules.length === 0 ? {} : resultsMap;
}
