"use client";

import { keepPreviousData } from "@tanstack/react-query";
import { dequal } from "dequal";
import { useMemo } from "react";
import { useDebounce } from "use-debounce";
import { $api } from "@/lib/api/browser";
import type { DocumentDef, RuleCheck, WorkflowRule } from "@/lib/types";

const DEBOUNCE_MS = 400;

/** API feedback on the draft rules (what blocks saving, each condition as text), by rule id.
 * The query key is the draft itself, so an unchanged draft is never checked twice. */
export function useRuleValidation(
  documents: DocumentDef[],
  rules: WorkflowRule[],
): Record<string, RuleCheck> {
  const [body] = useDebounce(
    useMemo(() => ({ documents, rules }), [documents, rules]),
    DEBOUNCE_MS,
    { equalityFn: dequal },
  );
  const { data } = $api.useQuery(
    "post",
    "/v1/workflows/check-rules",
    { body },
    {
      enabled: body.rules.length > 0,
      placeholderData: keepPreviousData,
      staleTime: Number.POSITIVE_INFINITY,
      retry: false,
    },
  );
  return useMemo(
    () => (rules.length && data ? Object.fromEntries(data.rules.map((r) => [r.ruleId, r])) : {}),
    [data, rules.length],
  );
}
