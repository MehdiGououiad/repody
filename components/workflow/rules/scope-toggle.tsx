"use client";

import { useTranslations } from "next-intl";
import { SegmentedControl, SegmentedControlOption } from "@/components/ui/segmented-control";
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
    <SegmentedControl
      aria-label={t("appliesTo")}
      value={scope}
      onValueChange={(next) => next && onChange(next as RuleScope)}
    >
      <SegmentedControlOption value="intra">{t("scopeIntraShort")}</SegmentedControlOption>
      <SegmentedControlOption
        value="cross"
        disabled={!canCross}
        title={canCross ? undefined : t("crossRequiresTwoDocs")}
      >
        {t("scopeCrossShort")}
      </SegmentedControlOption>
    </SegmentedControl>
  );
}
