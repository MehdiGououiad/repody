"use client";

import { motion } from "motion/react";
import Link from "next/link";
import { useFormatter, useTranslations } from "next-intl";
import { EASE_OUT } from "@/lib/motion";
import type { Dashboard } from "@/lib/types";
import { cn } from "@/lib/utils";

const PARTS = [
  { key: "passed", color: "bg-pass" },
  { key: "warning", color: "bg-warn" },
  { key: "failed", color: "bg-fail" },
] as const;

/** Fourteen days of runs, each bar split by outcome; this week is full strength, the last one faded. */
export function VolumeChart({ series }: { series: Dashboard["performanceSeries"] }) {
  const t = useTranslations("dashboard.volume");
  const format = useFormatter();
  const max = Math.max(1, ...series.map((d) => d.runs));
  const ticks = [max, Math.round(max / 2), 0];

  return (
    <figure className="flex h-full flex-col gap-3">
      <div className="flex min-h-0 flex-1 gap-2">
        <div className="flex flex-col justify-between pb-5 text-end text-2xs tabular-nums text-ink-4">
          {ticks.map((tick) => (
            <span key={tick}>{tick}</span>
          ))}
        </div>
        <div className="relative grid min-h-40 flex-1 grid-cols-14 items-end gap-1.5">
          <div
            className="pointer-events-none absolute inset-x-0 top-0 bottom-5 flex flex-col justify-between"
            aria-hidden
          >
            {ticks.map((tick) => (
              <span key={tick} className="h-px w-full bg-line" />
            ))}
          </div>
          {series.map((day, i) => {
            const date = new Date(`${day.day}T00:00:00Z`);
            const label = t("bar", {
              day: format.dateTime(date, {
                weekday: "long",
                day: "numeric",
                month: "long",
                timeZone: "UTC",
              }),
              runs: day.runs,
            });
            const thisWeek = i >= series.length - 7;
            const today = i === series.length - 1;
            return (
              <Link
                key={day.day}
                href={`/audits?day=${day.day}`}
                aria-label={label}
                title={`${label} · ${day.passed} / ${day.warning} / ${day.failed}`}
                className="group relative z-10 flex h-full flex-col justify-end gap-1"
              >
                <motion.span
                  className={cn(
                    "flex w-full flex-col-reverse overflow-hidden rounded-[3px] transition-opacity duration-150 group-hover:opacity-100",
                    thisWeek ? "opacity-100" : "opacity-45",
                  )}
                  initial={{ height: 0 }}
                  animate={{ height: `calc((100% - 1.25rem) * ${day.runs / max})` }}
                  transition={{ duration: 0.5, ease: EASE_OUT, delay: i * 0.025 }}
                >
                  {PARTS.map((part) =>
                    day[part.key] ? (
                      <span
                        key={part.key}
                        className={part.color}
                        style={{ flexGrow: day[part.key] }}
                      />
                    ) : null,
                  )}
                  {day.runs > day.passed + day.warning + day.failed ? (
                    <span
                      className="bg-ink-4"
                      style={{ flexGrow: day.runs - day.passed - day.warning - day.failed }}
                    />
                  ) : null}
                </motion.span>
                {day.runs === 0 ? (
                  <span className="h-0.5 w-full rounded-full bg-line-strong" />
                ) : null}
                <span
                  className={cn(
                    "h-4 text-center text-2xs tabular-nums",
                    today ? "font-semibold text-ink" : "text-ink-4 group-hover:text-ink-2",
                  )}
                >
                  {format.dateTime(date, { day: "numeric", timeZone: "UTC" })}
                </span>
              </Link>
            );
          })}
        </div>
      </div>
      <figcaption className="flex flex-wrap gap-4 ps-6 text-xs text-ink-3">
        {PARTS.map((part) => (
          <span key={part.key} className="flex items-center gap-1.5">
            <span className={cn("size-2 rounded-[2px]", part.color)} aria-hidden />
            {t(part.key)}
            <span className="tabular-nums text-ink-2">
              {series.slice(-7).reduce((sum, d) => sum + d[part.key], 0)}
            </span>
          </span>
        ))}
      </figcaption>
    </figure>
  );
}
