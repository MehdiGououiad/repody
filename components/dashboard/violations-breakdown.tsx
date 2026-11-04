"use client";

import { useTranslations } from "next-intl";
import type { SeverityShare } from "@/lib/types";
import { cn } from "@/lib/utils";

const COLORS: Record<string, string> = { reject: "bg-danger", flag: "bg-warning" };

/** Share of this week's rule failures by severity. */
export function ViolationsBreakdown({ items }: { items: SeverityShare[] }) {
  const t = useTranslations("dashboard.violations");
  return (
    <div className="panel-elevated rounded-xl flex flex-col">
      <div className="px-4 py-3 border-b border-border/70">
        <h3 className="font-display text-sm font-semibold">{t("title")}</h3>
        <p className="text-xs text-on-surface-variant mt-0.5">{t("hint")}</p>
      </div>
      <div className="p-4 flex flex-col gap-4">
        {items.length === 0 ? <p className="text-sm text-on-surface-variant">{t("none")}</p> : null}
        {items.map((it) => {
          const pct = Math.round(it.share * 1000) / 10;
          const color = COLORS[it.severity] ?? "bg-outline-variant";
          return (
            <div key={it.severity} className="space-y-1.5">
              <div className="flex items-center gap-3">
                <div className={cn("w-2.5 h-2.5 rounded-full", color)} />
                <span className="text-sm text-on-surface flex-1">
                  {it.severity === "reject" ? t("reject") : t("flag")}
                </span>
                <span className="text-xs font-semibold tabular-nums">{pct}%</span>
              </div>
              <div className="w-full bg-surface-container-high h-1.5 rounded-full overflow-hidden">
                <div className={cn("h-full", color)} style={{ width: `${pct}%` }} />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
