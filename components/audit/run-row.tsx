"use client";

import Link from "next/link";
import { useFormatter, useNow, useTranslations } from "next-intl";
import { StatusGlyph } from "@/components/ui/status-glyph";
import type { Audit } from "@/lib/types";

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

/** One run in a list: status glyph, workflow, what failed, how many fields, when. */
function RunRow({ audit }: { audit: Audit }) {
  const t = useTranslations("audits");
  const format = useFormatter();
  return (
    <li>
      <Link
        href={`/audits/${audit.id}`}
        className="group grid h-10 grid-cols-[14px_minmax(0,1fr)_auto] items-center gap-3 px-4 transition-colors duration-100 hover:bg-hover md:grid-cols-[14px_minmax(0,1.4fr)_minmax(0,1fr)_88px_88px] md:px-5"
      >
        <StatusGlyph status={audit.status} label={t(`status.${audit.status}`)} />
        <span className="min-w-0 truncate text-sm font-medium text-ink">{audit.workflowName}</span>
        <span className="hidden min-w-0 truncate text-sm text-ink-3 md:block">
          {audit.failedRules
            ? t("row.failedRules", { count: audit.failedRules })
            : t(`status.${audit.status}`)}
        </span>
        <span className="hidden text-end text-xs tabular-nums text-ink-3 md:block">
          {t("row.fields", { count: audit.rows, formatted: format.number(audit.rows) })}
        </span>
        <span className="text-end text-xs tabular-nums text-ink-3">
          <When value={audit.timestamp} />
        </span>
      </Link>
    </li>
  );
}

export function RunRows({ audits }: { audits: Audit[] }) {
  return (
    <ul className="divide-y divide-line">
      {audits.map((audit) => (
        <RunRow key={audit.id} audit={audit} />
      ))}
    </ul>
  );
}
