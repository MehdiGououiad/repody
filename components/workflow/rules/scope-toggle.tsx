"use client";

import { FileText, GitCompare } from "lucide-react";
import { useTranslations } from "next-intl";
import type { RuleScope } from "@/lib/types";
import { cn } from "@/lib/utils";

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
    <div className="flex rounded-lg border border-line overflow-hidden w-fit text-2xs font-medium">
      <button
        type="button"
        aria-pressed={scope === "intra"}
        onClick={() => onChange("intra")}
        className={cn(
          "flex items-center gap-1.5 px-3 py-1.5 transition-colors",
          scope === "intra" ? "bg-accent text-on-accent" : "bg-raised text-ink-3 hover:bg-panel"
        )}
      >
        <FileText className="h-3 w-3" />
        {t("scopeIntraShort")}
      </button>
      <div className="w-px bg-line" />
      <button
        type="button"
        aria-pressed={scope === "cross"}
        aria-disabled={!canCross}
        onClick={() => canCross && onChange("cross")}
        title={!canCross ? t("crossRequiresTwoDocs") : undefined}
        className={cn(
          "flex items-center gap-1.5 px-3 py-1.5 transition-colors",
          scope === "cross" ? "bg-accent text-on-accent" : "bg-raised text-ink-3",
          canCross ? "hover:bg-panel" : "opacity-40 cursor-not-allowed"
        )}
      >
        <GitCompare className="h-3 w-3" />
        {t("scopeCrossShort")}
      </button>
    </div>
  );
}
