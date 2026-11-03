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
    <div className="flex rounded-lg border border-border overflow-hidden w-fit text-[11px] font-medium">
      <button
        type="button"
        aria-pressed={scope === "intra"}
        onClick={() => onChange("intra")}
        className={cn(
          "flex items-center gap-1.5 px-3 py-1.5 transition-colors",
          scope === "intra"
            ? "bg-primary text-primary-foreground"
            : "bg-surface-container-low text-on-surface-variant hover:bg-surface-bright"
        )}
      >
        <FileText className="h-3 w-3" />
        {t("scopeIntraShort")}
      </button>
      <div className="w-px bg-border" />
      <button
        type="button"
        aria-pressed={scope === "cross"}
        aria-disabled={!canCross}
        onClick={() => canCross && onChange("cross")}
        title={!canCross ? t("crossRequiresTwoDocs") : undefined}
        className={cn(
          "flex items-center gap-1.5 px-3 py-1.5 transition-colors",
          scope === "cross"
            ? "bg-primary text-primary-foreground"
            : "bg-surface-container-low text-on-surface-variant",
          canCross ? "hover:bg-surface-bright" : "opacity-40 cursor-not-allowed"
        )}
      >
        <GitCompare className="h-3 w-3" />
        {t("scopeCrossShort")}
      </button>
    </div>
  );
}
