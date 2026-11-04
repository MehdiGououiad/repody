"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { queryKeys } from "@/lib/hooks/query-keys";
import {
  type RuleValidationResult,
  resultsByRuleId,
  validateRulesViaApi,
} from "@/lib/rules/rule-preview";
import type { DocumentDef, WorkflowRule } from "@/lib/types";
import { rulesValidationFingerprint } from "@/lib/workflow/draft-fingerprint";

const DEBOUNCE_MS = 400;

function useDebounced<T>(value: T, ms: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = window.setTimeout(() => setDebounced(value), ms);
    return () => window.clearTimeout(timer);
  }, [value, ms]);
  return debounced;
}

/** Backend feedback on the draft rules (issues and readable conditions), by rule id. */
export function useRuleValidation(
  documents: DocumentDef[],
  rules: WorkflowRule[]
): Record<string, RuleValidationResult> {
  const fingerprint = useMemo(
    () => rulesValidationFingerprint(documents, rules),
    [documents, rules]
  );
  const key = useDebounced(fingerprint, DEBOUNCE_MS);
  const { data } = useQuery({
    queryKey: queryKeys.checkRules(key),
    queryFn: async () => resultsByRuleId(await validateRulesViaApi(documents, rules)),
    enabled: rules.length > 0,
    placeholderData: keepPreviousData,
    staleTime: Number.POSITIVE_INFINITY,
    retry: false,
  });
  return rules.length > 0 ? (data ?? {}) : {};
}
