"use client";

import { useState } from "react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { AlertOctagon, AlertTriangle, Info, X, ArrowRight } from "lucide-react";
import type { HealthAlert } from "@/lib/types";
import { cn } from "@/lib/utils";

const sevConfig = {
  danger: {
    Icon: AlertOctagon,
    className: "bg-danger-soft text-danger-strong border-danger/30",
    iconClass: "text-danger",
  },
  warning: {
    Icon: AlertTriangle,
    className: "bg-warning-soft text-warning-strong border-warning/30",
    iconClass: "text-warning-strong",
  },
  info: {
    Icon: Info,
    className: "bg-info-soft text-info border-info/20",
    iconClass: "text-info",
  },
} as const;

export function HealthStrip({ alerts }: { alerts: HealthAlert[] }) {
  const t = useTranslations("health");
  const tCommon = useTranslations("common");
  const [dismissed, setDismissed] = useState<Set<string>>(new Set());
  const visible = alerts.filter((a) => !dismissed.has(a.id));
  if (!visible.length) return null;

  return (
    <div className="flex flex-col gap-2">
      {visible.map((a) => {
        const cfg = sevConfig[a.severity];
        const Inner = (
          <>
            <cfg.Icon className={cn("h-4 w-4 shrink-0", cfg.iconClass)} />
            <div className="flex-1 min-w-0">
              <p className="font-semibold text-sm leading-tight">
                {t(a.titleKey as "degraded")}
              </p>
              <p className="text-xs opacity-80 mt-0.5">
                {t(a.detailKey as "degradedDetail")}
              </p>
            </div>
            {a.href ? <ArrowRight className="h-4 w-4 opacity-70" /> : null}
          </>
        );
        return (
          <div
            key={a.id}
            className={cn(
              "flex items-center gap-3 px-4 py-2.5 rounded-md border",
              cfg.className
            )}
          >
            {a.href ? (
              <Link href={a.href} className="flex items-center gap-3 flex-1 min-w-0">
                {Inner}
              </Link>
            ) : (
              <div className="flex items-center gap-3 flex-1 min-w-0">{Inner}</div>
            )}
            <button
              type="button"
              onClick={() => setDismissed((s) => new Set(s).add(a.id))}
              className="opacity-60 hover:opacity-100"
              aria-label={tCommon("dismiss")}
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
        );
      })}
    </div>
  );
}
