"use client";

import { useId, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { BarChart3 } from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  Cell,
} from "recharts";
import { Button } from "@/components/ui/button";
import { ChartContainer } from "@/components/dashboard/chart-container";
import type { PerformancePoint } from "@/lib/types";

export function PerformanceChart({ data }: { data: PerformancePoint[] }) {
  const t = useTranslations("dashboard.performance");
  const router = useRouter();
  const [compare, setCompare] = useState(false);
  const chartId = useId();
  const peakColor = "var(--accent-blue)";
  const baseColor = "var(--primary-stitch)";
  const prevColor = "var(--outline-variant)";

  const peakIdx = data.length
    ? data.reduce((max, d, i) => (d.runs > data[max].runs ? i : max), 0)
    : 0;
  const totalRuns = useMemo(
    () => data.reduce((sum, point) => sum + point.runs, 0),
    [data]
  );
  const peakDay = data[peakIdx]?.day ?? "";
  const peakRuns = data[peakIdx]?.runs ?? 0;

  if (data.length === 0) {
    return (
      <div className="panel-elevated rounded-xl flex flex-col">
        <div className="px-4 py-3 border-b border-border/70">
          <h3 className="font-display text-sm font-semibold">{t("title")}</h3>
          <p className="text-xs text-on-surface-variant mt-0.5">{t("hint")}</p>
        </div>
        <div className="flex flex-col items-center justify-center gap-3 p-10 text-center min-h-[300px]">
          <BarChart3 className="h-8 w-8 text-outline-variant" aria-hidden="true" />
          <p className="text-sm font-medium text-on-surface">{t("emptyTitle")}</p>
          <p className="text-xs text-on-surface-variant max-w-xs">{t("emptyHint")}</p>
        </div>
      </div>
    );
  }

  return (
    <figure className="panel-elevated rounded-xl flex flex-col" aria-labelledby={chartId}>
      <div className="flex items-center justify-between px-4 py-3 border-b border-border/70">
        <div>
          <h3 id={chartId} className="font-display text-sm font-semibold">
            {t("title")}
          </h3>
          <p className="text-xs text-on-surface-variant mt-0.5">{t("hint")}</p>
        </div>
        <Button
          variant={compare ? "secondary" : "outline"}
          size="sm"
          aria-pressed={compare}
          onClick={() => setCompare((v) => !v)}
        >
          {compare ? t("compareOn") : t("compareOff")}
        </Button>
      </div>
      <figcaption className="sr-only">
        {t("summary", { total: totalRuns, peakDay, peakRuns })}
      </figcaption>
      <ChartContainer
        className="p-4 h-[300px] cursor-pointer"
        role="img"
        aria-label={t("summary", { total: totalRuns, peakDay, peakRuns })}
      >
        <ResponsiveContainer
          width="100%"
          height="100%"
          minWidth={0}
          minHeight={268}
          initialDimension={{ width: 640, height: 268 }}
        >
          <BarChart
            data={data}
            barGap={4}
            margin={{ top: 8, right: 8, left: -16, bottom: 0 }}
            onClick={(e) => {
              if (e?.activeLabel) {
                router.push(`/audits?day=${e.activeLabel}`);
              }
            }}
          >
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="var(--border)"
              vertical={false}
            />
            <XAxis
              dataKey="day"
              tickLine={false}
              axisLine={false}
              tick={{ fontSize: 11, fill: "var(--on-surface-variant)" }}
            />
            <YAxis
              tickLine={false}
              axisLine={false}
              tick={{ fontSize: 11, fill: "var(--on-surface-variant)" }}
            />
            <Tooltip
              cursor={{ fill: "var(--surface-container-low)" }}
              contentStyle={{
                background: "var(--popover)",
                border: "1px solid var(--border)",
                borderRadius: 8,
                fontSize: 12,
                color: "var(--foreground)",
              }}
              formatter={(value, name) => [
                Number(value).toLocaleString(),
                name === "runs" ? t("runs") : t("previousPeriod"),
              ]}
            />
            {compare ? (
              <Bar
                dataKey="prevRuns"
                name={t("previousPeriod")}
                fill={prevColor}
                radius={[3, 3, 0, 0]}
              />
            ) : null}
            <Bar dataKey="runs" name={t("runs")} radius={[3, 3, 0, 0]}>
              {data.map((point, i) => (
                <Cell
                  key={point.day}
                  fill={i === peakIdx ? peakColor : baseColor}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </ChartContainer>
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 px-4 pb-3 text-[11px] text-on-surface-variant">
        <span className="inline-flex items-center gap-1.5">
          <span
            className="size-2.5 rounded-sm shrink-0"
            style={{ background: baseColor }}
            aria-hidden="true"
          />
          {t("runs")}
        </span>
        {compare ? (
          <span className="inline-flex items-center gap-1.5">
            <span
              className="size-2.5 rounded-sm shrink-0"
              style={{ background: prevColor }}
              aria-hidden="true"
            />
            {t("previousPeriod")}
          </span>
        ) : null}
        <span className="inline-flex items-center gap-1.5">
          <span
            className="size-2.5 rounded-sm shrink-0"
            style={{ background: peakColor }}
            aria-hidden="true"
          />
          {t("peakDay")}
        </span>
      </div>
    </figure>
  );
}
