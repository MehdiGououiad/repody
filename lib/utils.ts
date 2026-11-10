import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

/** A run duration: "850ms", "4.2s", "3m 5s" (units are universal, no locale needed). */
export function formatDurationMs(ms: number | null | undefined): string {
  if (ms == null) return "—";
  if (ms < 1000) return `${ms}ms`;
  const s = ms / 1000;
  if (s < 60) return `${s.toFixed(1)}s`;
  return `${Math.floor(s / 60)}m ${Math.round(s % 60)}s`;
}

/** Byte size with Intl unit formatting, e.g. "512 byte", "300 kB", "25 MB". */
export function formatBytes(bytes: number, locale: string): string {
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

export function shortId(): string {
  return crypto.randomUUID().slice(0, 8);
}

/** An extracted value for display: numbers in the reader's locale, tables and lists as JSON. */
export function formatExtractedFieldValue(value: unknown, locale: string): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "number") return new Intl.NumberFormat(locale).format(value);
  if (typeof value === "string") return value;
  return JSON.stringify(value);
}
