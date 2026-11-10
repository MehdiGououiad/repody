"use client";

import { CheckCircle2, Gavel, GitBranch, TrendingDown, TrendingUp } from "lucide-react";
import { useTranslations } from "next-intl";
import { Area, AreaChart, ResponsiveContainer } from "recharts";
import { ChartContainer } from "@/components/dashboard/chart-container";
import type { Kpi } from "@/lib/types";
import { cn } from "@/lib/utils";

const ICONS: Record<Kpi["id"], React.ElementType> = {
  auditsWeek: GitBranch,
  passRate: CheckCircle2,
  failures: Gavel,
};

/** Where fewer is better, a drop is good news. */
const LOWER_IS_BETTER = new Set<Kpi["id"]>(["failures"]);

function formatKpi(id: Kpi["id"], value: number): string {
  return id === "passRate" ? `${(value * 100).toFixed(1)}%` : String(Math.round(value));
}

export function KpiCard({ metric }: { metric: Kpi }) {
  const t = useTranslations("dashboard.kpi");
  const Icon = ICONS[metric.id];
  const change = metric.value - metric.previous;
  const TrendIcon = change >= 0 ? TrendingUp : TrendingDown;
  const deltaStr =
    metric.id === "passRate" ? `${(change * 100).toFixed(1)} pts` : `${Math.round(change)}`;
  const positive = LOWER_IS_BETTER.has(metric.id) ? change <= 0 : change >= 0;
  const trendColor = positive ? "var(--success)" : "var(--danger)";
  const trendLabel = positive
    ? t("trendUp", { delta: deltaStr })
    : t("trendDown", { delta: deltaStr });

  return (
    <div className="panel-elevated rounded-xl p-4 hover:border-accent-blue/25 transition-[border-color,box-shadow] duration-200 flex flex-col gap-3 overflow-hidden relative group">
      <div className="flex items-start justify-between">
        <span className="text-[11px] font-semibold tracking-wider uppercase text-on-surface-variant">
          {t(metric.id)}
        </span>
        <Icon className="h-4 w-4 text-outline-variant" aria-hidden="true" />
      </div>
      <div className="flex items-baseline gap-2">
        <span className="font-display text-2xl font-semibold text-on-surface tracking-tight tabular-nums">
          {formatKpi(metric.id, metric.value)}
        </span>
        <span
          className={cn(
            "inline-flex items-center gap-0.5 text-xs font-semibold tabular-nums",
            positive ? "text-success" : "text-danger"
          )}
        >
          <TrendIcon className="h-3 w-3" aria-hidden="true" />
          {deltaStr}
          <span className="sr-only">{trendLabel}</span>
        </span>
      </div>
      <ChartContainer className="h-10 -mx-1 -mb-1">
        <ResponsiveContainer
          width="100%"
          height={40}
          minWidth={0}
          initialDimension={{ width: 240, height: 40 }}
        >
          <AreaChart data={metric.series} margin={{ top: 4, right: 4, bottom: 0, left: 4 }}>
            <defs>
              <linearGradient id={`spark-${metric.id}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={trendColor} stopOpacity={0.35} />
                <stop offset="100%" stopColor={trendColor} stopOpacity={0} />
              </linearGradient>
            </defs>
            <Area
              type="monotone"
              dataKey="value"
              stroke={trendColor}
              strokeWidth={1.5}
              fill={`url(#spark-${metric.id})`}
              isAnimationActive={false}
            />
          </AreaChart>
        </ResponsiveContainer>
      </ChartContainer>
    </div>
  );
}
