"use client";

import { type DateTimeFormatOptions, useFormatter } from "next-intl";

const DEFAULT_FORMAT: DateTimeFormatOptions = { dateStyle: "medium", timeStyle: "short" };

/**
 * A moment in the reader's locale and time zone. Server and browser format it with the same zone,
 * but their time-zone data can still differ (a country's rules change before both update), so a
 * differing text is accepted on hydration instead of rebuilding the page.
 */
export function DateTime({
  value,
  format = DEFAULT_FORMAT,
}: {
  value: string | Date;
  format?: DateTimeFormatOptions;
}) {
  const formatter = useFormatter();
  const date = typeof value === "string" ? new Date(value) : value;
  return (
    <time dateTime={date.toISOString()} suppressHydrationWarning>
      {formatter.dateTime(date, format)}
    </time>
  );
}
