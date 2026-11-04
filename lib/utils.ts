import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

export type LocaleArg = string | undefined;

export function formatNumber(n: number, locale: LocaleArg = "en-US"): string {
  return new Intl.NumberFormat(locale).format(n);
}

export function formatPercent(n: number, fractionDigits = 1, locale: LocaleArg = "en-US"): string {
  return new Intl.NumberFormat(locale, {
    style: "percent",
    minimumFractionDigits: fractionDigits,
    maximumFractionDigits: fractionDigits,
  }).format(n);
}

export function formatDurationMs(ms: number | null | undefined): string {
  if (ms == null) return "—";
  if (ms < 1000) return `${ms}ms`;
  const s = ms / 1000;
  if (s < 60) return `${s.toFixed(1)}s`;
  const m = Math.floor(s / 60);
  const rem = Math.round(s % 60);
  return `${m}m ${rem}s`;
}

/** Byte size with Intl unit formatting, e.g. "512 byte", "300 kB", "25 MB". */
export function formatBytes(bytes: number, locale: LocaleArg = "en-US"): string {
  const [value, unit] =
    bytes < 1024
      ? [bytes, "byte"]
      : bytes < 1024 ** 2
        ? [bytes / 1024, "kilobyte"]
        : [bytes / 1024 ** 2, "megabyte"];
  return new Intl.NumberFormat(locale, {
    style: "unit",
    unit,
    maximumFractionDigits: unit === "megabyte" ? 1 : 0,
  }).format(value);
}

/** Short 24h timestamp for tables, e.g. "Oct 24, 14:32" (optionally with the year). */
export function formatDateTime(
  iso: string,
  locale: LocaleArg = "en-US",
  { withYear = false }: { withYear?: boolean } = {}
): string {
  return new Date(iso).toLocaleString(locale, {
    ...(withYear ? { year: "numeric" } : {}),
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

export function shortId(): string {
  return crypto.randomUUID().slice(0, 8);
}

/** An extracted value for display: numbers in the reader's locale, tables and lists as JSON. */
export function formatExtractedFieldValue(value: unknown, locale: LocaleArg = "en-US"): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "number") return new Intl.NumberFormat(locale).format(value);
  if (typeof value === "string") return value;
  return JSON.stringify(value);
}
