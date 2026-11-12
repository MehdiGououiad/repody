"use client";

import { useTranslations } from "next-intl";
import { Segmented } from "@/components/ui/segmented";
import type { RuleScope } from "@/lib/types";

/** Whether a rule checks one document or compares two. */
export function ScopeToggle({
  scope,
  onChange,
  canCross,
}: {
  scope: RuleScope;
  onChange: (s: RuleScope) => void;
  canCross: boolean;
}) {
  const t = useTranslations("workflows.builder.rules");
  return (
    <Segmented
      label={t("appliesTo")}
      value={scope}
      onChange={onChange}
      options={[
        { value: "intra", label: t("scopeIntraShort") },
        {
          value: "cross",
          label: t("scopeCrossShort"),
          disabled: !canCross,
          title: canCross ? undefined : t("crossRequiresTwoDocs"),
        },
      ]}
    />
  );
}
