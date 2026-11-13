"use client";

import { motion } from "motion/react";
import Link from "next/link";
import { useFormatter, useNow, useTranslations } from "next-intl";
import { StatusGlyph } from "@/components/ui/status-glyph";
import { rowEnter } from "@/lib/motion";
import type { Audit } from "@/lib/types";
import { cn, formatDurationMs } from "@/lib/utils";

/** When it happened, relative while recent ("5 min ago"), a date after a week. */
export function When({ value }: { value: string }) {
  const format = useFormatter();
  const now = useNow({ updateInterval: 60_000 });
  const date = new Date(value);
  const recent = now.getTime() - date.getTime() < 7 * 24 * 3600 * 1000;
  return (
    <time
      dateTime={date.toISOString()}
      title={format.dateTime(date, { dateStyle: "full", timeStyle: "short" })}
      suppressHydrationWarning
    >
      {recent
        ? format.relativeTime(date, now)
        : format.dateTime(date, { day: "numeric", month: "short" })}
    </time>
  );
}

/** Why a run looks the way it does, in one phrase: the failing rule, or nothing read, or the count. */
function Reason({ audit }: { audit: Audit }) {
  const t = useTranslations("audits.row");
  if (audit.firstFailedRule) {
    return (
      <span
        className={cn("truncate", audit.status === "failed" ? "text-fail-ink" : "text-warn-ink")}
      >
        {audit.firstFailedRule}
        {audit.failedRules > 1 ? (
          <span className="text-ink-4"> +{audit.failedRules - 1}</span>
        ) : null}
      </span>
    );
  }
  if (!audit.rows) return <span className="truncate text-warn-ink">{t("noFields")}</span>;
  return <span className="truncate text-ink-4">{t("fields", { count: audit.rows })}</span>;
}

/** One run: glyph, short id, workflow and files, why, source, duration, when. 32px, keyboard reachable. */
export function RunRow({ audit, index }: { audit: Audit; index: number }) {
  const t = useTranslations("audits");
  const files = audit.files.join(", ");
  return (
    <motion.li {...rowEnter(index)}>
      <Link
        href={`/audits/${audit.id}`}
        data-row
        className={cn(
          "group grid h-8 grid-cols-[14px_minmax(0,1fr)_auto] items-center gap-3 px-4 text-[13px] outline-none transition-colors duration-100 hover:bg-hover focus-visible:bg-selected md:grid-cols-[14px_56px_minmax(0,1.3fr)_minmax(0,1fr)_44px_52px_80px] md:px-5",
          audit.status === "failed" && "bg-fail-wash/40",
          audit.status === "warning" && "bg-warn-wash/40"
        )}
      >
        <StatusGlyph status={audit.status} label={t(`status.${audit.status}`)} />
        <span className="hidden font-mono text-xs text-ink-4 md:block">{audit.id.slice(-6)}</span>
        <span className="flex min-w-0 items-baseline gap-2">
          <span className="truncate font-medium text-ink">{audit.workflowName}</span>
          {files ? (
            <span className="hidden truncate text-xs text-ink-3 sm:inline">{files}</span>
          ) : null}
        </span>
        <span className="hidden min-w-0 md:flex">
          <Reason audit={audit} />
        </span>
        <span className="hidden md:block">
          <span
            className={cn(
              "inline-flex h-4.5 items-center rounded-sm px-1.5 text-2xs font-medium",
              audit.source === "api" ? "bg-accent-wash text-accent-ink" : "bg-selected text-ink-3"
            )}
          >
            {t(`row.source.${audit.source}`)}
          </span>
        </span>
        <span className="hidden text-end text-xs tabular-nums text-ink-3 md:block">
          {audit.durationMs ? formatDurationMs(audit.durationMs) : "—"}
        </span>
        <span className="text-end text-xs tabular-nums text-ink-3">
          <When value={audit.timestamp} />
        </span>
      </Link>
    </motion.li>
  );
}

/** Runs grouped by day under sticky headers: today, yesterday, then the date. */
export function RunGroups({
  audits,
  stickyTop = "top-0",
}: {
  audits: Audit[];
  stickyTop?: string;
}) {
  const t = useTranslations("audits.groups");
  const format = useFormatter();
  const now = useNow({ updateInterval: 60_000 });
  const dayKey = (d: Date) => d.toISOString().slice(0, 10);
  const today = dayKey(now);
  const yesterday = dayKey(new Date(now.getTime() - 86_400_000));
  const groups = new Map<string, Audit[]>();
  for (const audit of audits) {
    const key = dayKey(new Date(audit.timestamp));
    groups.set(key, [...(groups.get(key) ?? []), audit]);
  }
  let index = 0;
  return (
    <div>
      {[...groups].map(([key, rows]) => (
        <section key={key} aria-label={key}>
          <h3
            className={cn(
              "sticky z-[5] flex h-7 items-center gap-2 border-y border-line bg-raised/95 px-4 text-xs font-semibold text-ink-2 backdrop-blur-sm md:px-5",
              stickyTop
            )}
          >
            {key === today
              ? t("today")
              : key === yesterday
                ? t("yesterday")
                : format.dateTime(new Date(`${key}T12:00:00Z`), {
                    weekday: "long",
                    day: "numeric",
                    month: "long",
                  })}
            <span className="font-normal tabular-nums text-ink-4">{rows.length}</span>
          </h3>
          <ul className="divide-y divide-line">
            {rows.map((audit) => (
              <RunRow key={audit.id} audit={audit} index={index++} />
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}
