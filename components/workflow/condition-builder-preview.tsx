"use client";

import { useTranslations } from "next-intl";
import { Code2 } from "lucide-react";
import { conditionToString } from "@/lib/rules/expression";
import type { RuleCondition } from "@/lib/types";

export function ConditionPreview({ conditions }: { conditions: RuleCondition[] }) {
  const t = useTranslations("workflows.builder.rules.conditions");

  if (conditions.some((condition) => conditionToString(condition))) {
    return (
      <div className="rounded-lg border border-border bg-surface-container-lowest px-3 py-2 space-y-1.5">
        <p className="text-[10px] text-on-surface-variant">{t("separateChecksHint")}</p>
        {conditions.map((condition, index) => {
          const line = conditionToString(condition);
          if (!line) return null;

          return (
            <div key={condition.id} className="flex items-start gap-2">
              <Code2 className="h-3.5 w-3.5 text-on-surface-variant mt-0.5 shrink-0" />
              <code className="text-[11px] font-mono text-on-surface-variant break-all">
                {t("checkN", { n: index + 1 })}: {line}
              </code>
            </div>
          );
        })}
      </div>
    );
  }

  if (conditions.some((condition) => condition.left?.value || condition.right?.value)) {
    return (
      <p className="text-[11px] text-danger rounded-lg border border-danger/30 bg-danger/5 px-3 py-2">
        {t("expressionIncomplete")}
      </p>
    );
  }

  return null;
}
