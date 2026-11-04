"use client";

import { AlertTriangle, ArrowRight } from "lucide-react";
import Link from "next/link";
import { useTranslations } from "next-intl";

/** Warns when runs are still `running` past their timeout (their worker stopped). */
export function HealthStrip({ staleRuns }: { staleRuns: number }) {
  const t = useTranslations("health.alerts.stale");
  if (!staleRuns) return null;
  return (
    <Link
      href="/audits"
      className="flex items-center gap-3 px-4 py-2.5 rounded-md border bg-warning-soft text-warning-strong border-warning/30"
    >
      <AlertTriangle className="h-4 w-4 shrink-0 text-warning-strong" />
      <div className="flex-1 min-w-0">
        <p className="font-semibold text-sm leading-tight">{t("title")}</p>
        <p className="text-xs opacity-80 mt-0.5">{t("detail", { count: staleRuns })}</p>
      </div>
      <ArrowRight className="h-4 w-4 opacity-70" />
    </Link>
  );
}
