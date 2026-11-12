"use client";

import Link from "next/link";
import { useFormatter, useTranslations } from "next-intl";
import type { Dashboard } from "@/lib/types";
import { cn } from "@/lib/utils";

type Point = Dashboard["performanceSeries"][number];

/**
 * Runs per day this week. Today carries the accent, the other days a neutral step, last week a
 * faint marker. Every bar is a link to that day's runs.
 */
export function VolumeChart({ data }: { data: Point[] }) {
  const t = useTranslations("dashboard.performance");
  const format = useFormatter();
  const max = Math.max(1, ...data.flatMap((p) => [p.runs, p.prevRuns]));
  const total = data.reduce((sum, p) => sum + p.runs, 0);

  return (
    <figure className="flex flex-col gap-2">
      <figcaption className="sr-only">{t("summaryShort", { total })}</figcaption>
      <div className="flex h-36 items-end gap-2 border-b border-line">
        {data.map((point, i) => {
          const today = i === data.length - 1;
          // Days are UTC dates; each is named by its weekday in the reader's locale.
          const date = new Date(`${point.day}T00:00:00Z`);
          const label = format.dateTime(date, { weekday: "long", timeZone: "UTC" });
          return (
            <Link
              key={point.day}
              href={`/audits?day=${point.day}`}
              aria-label={t("barLabel", { day: label, count: point.runs })}
              title={t("barLabel", { day: label, count: point.runs })}
              className="group relative flex h-full flex-1 items-end justify-center rounded-t-sm transition-colors duration-100 hover:bg-hover"
            >
              <span
                className="absolute inset-x-1 border-t border-dashed border-ink-4"
                style={{ bottom: `${(point.prevRuns / max) * 100}%` }}
                aria-hidden
              />
              <span
                className={cn(
                  "w-full max-w-10 rounded-t-sm",
                  today ? "bg-accent" : "bg-ink-4/45 group-hover:bg-ink-4/70"
                )}
                style={{ height: `${Math.max((point.runs / max) * 100, point.runs ? 3 : 0)}%` }}
              />
            </Link>
          );
        })}
      </div>
      <div className="flex gap-2 text-2xs text-ink-3">
        {data.map((point) => (
          <span key={point.day} className="flex-1 text-center tabular-nums">
            {format.dateTime(new Date(`${point.day}T00:00:00Z`), {
              weekday: "short",
              timeZone: "UTC",
            })}
          </span>
        ))}
      </div>
    </figure>
  );
}
