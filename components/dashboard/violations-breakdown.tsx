"use client";

import { useTranslations } from "next-intl";
import { cn } from "@/lib/utils";
import type { ViolationBreakdown } from "@/lib/types";

const colorMap = {
  danger: "bg-danger",
  warning: "bg-warning",
  info: "bg-accent-blue",
  neutral: "bg-outline-variant",
} as const;

const TYPE_KEYS = ["format", "missing", "logic", "llm", "other", "none"] as const;
type ViolationTypeKey = (typeof TYPE_KEYS)[number];

function violationTypeLabel(
  t: ReturnType<typeof useTranslations<"dashboard.violations">>,
  type: string
) {
  if ((TYPE_KEYS as readonly string[]).includes(type)) {
    return t(`types.${type as ViolationTypeKey}`);
  }
  return t("types.other");
}

export function ViolationsBreakdown({ items }: { items: ViolationBreakdown[] }) {
  const t = useTranslations("dashboard.violations");
  return (
    <div className="panel-elevated rounded-xl flex flex-col">
      <div className="px-4 py-3 border-b border-border/70">
        <h3 className="font-display text-sm font-semibold">{t("title")}</h3>
        <p className="text-xs text-on-surface-variant mt-0.5">{t("hint")}</p>
      </div>
      <div className="p-4 flex flex-col gap-4">
        {items.map((it) => (
          <div key={it.type} className="space-y-1.5">
            <div className="flex items-center gap-3">
              <div className={cn("w-2.5 h-2.5 rounded-full", colorMap[it.color])} />
              <span className="text-sm text-on-surface flex-1">
                {violationTypeLabel(t, it.type)}
              </span>
              <span className="text-xs font-semibold tabular-nums">
                {it.share}%
              </span>
            </div>
            <div className="w-full bg-surface-container-high h-1.5 rounded-full overflow-hidden">
              <div
                className={cn("h-full", colorMap[it.color])}
                style={{ width: `${it.share}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
