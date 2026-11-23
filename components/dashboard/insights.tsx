"use client";

import { AnimatePresence, motion } from "motion/react";
import Link from "next/link";
import { useFormatter, useTranslations } from "next-intl";
import { Fragment } from "react";
import { When } from "@/components/audit/run-row";
import { DocChip } from "@/components/shared/doc-chip";
import { StatusGlyph } from "@/components/ui/status-glyph";
import { docColor } from "@/lib/doc-color";
import { EASE_OUT } from "@/lib/motion";
import type { Audit, Dashboard } from "@/lib/types";
import { cn } from "@/lib/utils";

export const card = "flex flex-col overflow-hidden rounded-xl bg-panel shadow-panel";

export function CardHeader({
  title,
  hint,
  action,
}: {
  title: string;
  hint?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex items-start justify-between gap-3 border-b border-line px-4 py-2.5">
      <div className="min-w-0">
        <h2 className="eyebrow text-ink-2">{title}</h2>
        {hint ? <p className="mt-0.5 text-xs text-ink-4">{hint}</p> : null}
      </div>
      {action}
    </div>
  );
}

function Empty({ children }: { children: React.ReactNode }) {
  return (
    <p className="flex flex-1 items-center gap-2 px-4 py-6 text-[13px] text-ink-3">
      <StatusGlyph status="passed" />
      {children}
    </p>
  );
}

const DAY_MS = 86_400_000;

/** Seven days by 24 hours, in the reader's time zone; each cell's strength is its run count. */
export function HourHeatmap({ hourly }: { hourly: Dashboard["hourly"] }) {
  const t = useTranslations("dashboard.hours");
  const format = useFormatter();
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const days = Array.from({ length: 7 }, (_, i) => new Date(today.getTime() - (6 - i) * DAY_MS));
  const grid = days.map(() => Array.from({ length: 24 }, () => 0));
  for (const cell of hourly) {
    const local = new Date(`${cell.day}T${String(cell.hour).padStart(2, "0")}:00:00Z`);
    const row = Math.round(
      (new Date(local.getFullYear(), local.getMonth(), local.getDate()).getTime() -
        days[0].getTime()) /
        DAY_MS
    );
    if (row >= 0 && row < 7) grid[row][local.getHours()] += cell.runs;
  }
  const max = Math.max(1, ...grid.flat());
  let peak = { row: 0, hour: 0, runs: 0 };
  for (const [row, hours] of grid.entries()) {
    for (const [hour, runs] of hours.entries()) {
      if (runs > peak.runs) peak = { row, hour, runs };
    }
  }
  const dayName = (d: Date) => format.dateTime(d, { weekday: "short" });

  return (
    <section className={card}>
      <CardHeader
        title={t("title")}
        hint={t("hint")}
        action={
          peak.runs ? (
            <span className="text-xs text-ink-3">
              {t("peak", {
                day: format.dateTime(days[peak.row], { weekday: "long" }),
                hour: peak.hour,
              })}
            </span>
          ) : null
        }
      />
      <div className="flex flex-col gap-2 p-4">
        <div className="grid grid-cols-[32px_repeat(24,minmax(0,1fr))] gap-[3px]">
          {days.map((day, row) => (
            <Fragment key={day.toISOString()}>
              <span className="text-2xs leading-[14px] text-ink-4">{dayName(day)}</span>
              {grid[row].map((runs, hour) => (
                <motion.span
                  // biome-ignore lint/suspicious/noArrayIndexKey: the hour is the cell's identity.
                  key={hour}
                  title={t("cell", { day: dayName(day), hour, runs })}
                  initial={{ opacity: 0, scale: 0.6 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ duration: 0.25, ease: EASE_OUT, delay: (hour + row) * 0.008 }}
                  className={cn("h-3.5 rounded-[3px]", runs ? "bg-accent" : "bg-selected")}
                  style={runs ? { opacity: 0.25 + 0.75 * (runs / max) } : undefined}
                />
              ))}
            </Fragment>
          ))}
          <span />
          {Array.from({ length: 24 }, (_, hour) => (
            // biome-ignore lint/suspicious/noArrayIndexKey: the hour is the label's identity.
            <span key={hour} className="text-center text-2xs tabular-nums text-ink-4">
              {hour % 6 === 0 ? hour : ""}
            </span>
          ))}
        </div>
        <div className="flex items-center justify-end gap-1.5 text-2xs text-ink-4">
          {t("less")}
          {[0.15, 0.4, 0.7, 1].map((o) => (
            <span key={o} className="size-2.5 rounded-[2px] bg-accent" style={{ opacity: o }} />
          ))}
          {t("more")}
        </div>
      </div>
    </section>
  );
}

/** What the model read this week: documents and pages, by document type. */
export function DocumentsRead({ stats }: { stats: Dashboard["documents"] }) {
  const t = useTranslations("dashboard.documents");
  const format = useFormatter();
  const top = Math.max(1, ...stats.byType.map((d) => d.documents));
  return (
    <section className={card}>
      <CardHeader title={t("title")} hint={t("hint")} />
      {stats.documents ? (
        <div className="flex flex-col gap-3 p-4">
          <div className="flex items-baseline gap-4">
            <span className="text-[22px] font-semibold leading-tight tracking-[-0.02em] tabular-nums text-ink">
              {format.number(stats.documents)}
            </span>
            <span className="text-xs text-ink-3">
              {t("documents", { count: stats.documents })} · {t("pages", { count: stats.pages })}
            </span>
          </div>
          <ul className="flex flex-col gap-2.5">
            {stats.byType.map((type, index) => (
              <li key={type.documentType} className="flex flex-col gap-1">
                <span className="flex items-baseline justify-between gap-3 text-[13px]">
                  <DocChip index={index}>{type.documentType}</DocChip>
                  <span className="shrink-0 text-xs tabular-nums text-ink-3">
                    {format.number(type.documents)} · {t("pages", { count: type.pages })}
                  </span>
                </span>
                <span className="h-1 overflow-hidden rounded-full bg-selected">
                  <motion.span
                    className={cn("block h-full rounded-full", docColor(index).dot)}
                    initial={{ width: 0 }}
                    animate={{ width: `${(type.documents / top) * 100}%` }}
                    transition={{ duration: 0.5, ease: EASE_OUT, delay: index * 0.05 }}
                  />
                </span>
              </li>
            ))}
          </ul>
        </div>
      ) : (
        <Empty>{t("empty")}</Empty>
      )}
    </section>
  );
}

/** The latest runs as a feed; a new one slides in at the top. */
export function Activity({ audits }: { audits: Audit[] }) {
  const t = useTranslations("dashboard.activity");
  const tAudits = useTranslations("audits");
  return (
    <section className={card}>
      <CardHeader
        title={t("title")}
        action={
          <span className="relative mt-1 flex size-1.5" aria-hidden>
            <span className="absolute inset-0 animate-ping rounded-full bg-pass opacity-60 motion-reduce:hidden" />
            <span className="relative size-1.5 rounded-full bg-pass" />
          </span>
        }
      />
      {audits.length ? (
        <ol className="flex flex-col">
          <AnimatePresence initial={false}>
            {audits.map((audit) => (
              <motion.li
                key={audit.id}
                layout="position"
                initial={{ opacity: 0, y: -8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.25, ease: EASE_OUT }}
                className="border-b border-line last:border-b-0"
              >
                <Link
                  href={`/audits/${audit.id}`}
                  className="grid grid-cols-[14px_minmax(0,1fr)_auto] items-center gap-x-3 px-4 py-2 transition-colors duration-100 hover:bg-hover"
                >
                  <StatusGlyph status={audit.status} label={tAudits(`status.${audit.status}`)} />
                  <span className="min-w-0">
                    <span className="block truncate text-[13px] font-medium text-ink">
                      {audit.workflowName}
                    </span>
                    <span
                      className={cn(
                        "block truncate text-xs",
                        audit.firstFailedRule || audit.uncheckedRule
                          ? audit.status === "failed"
                            ? "text-fail-ink"
                            : "text-warn-ink"
                          : "text-ink-4"
                      )}
                    >
                      {audit.firstFailedRule ??
                        (audit.uncheckedRule
                          ? tAudits("row.unchecked", { rule: audit.uncheckedRule })
                          : audit.files.join(", ") || tAudits(`row.source.${audit.source}`))}
                    </span>
                  </span>
                  <span className="text-xs tabular-nums text-ink-4">
                    <When value={audit.timestamp} />
                  </span>
                </Link>
              </motion.li>
            ))}
          </AnimatePresence>
        </ol>
      ) : (
        <p className="px-4 py-6 text-[13px] text-ink-3">{t("empty")}</p>
      )}
    </section>
  );
}
