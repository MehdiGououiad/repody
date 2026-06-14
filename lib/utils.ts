import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

export function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export type LocaleArg = string | undefined;

export function formatNumber(n: number, locale: LocaleArg = "en-US"): string {
  return new Intl.NumberFormat(locale).format(n);
}

export function formatCurrency(
  n: number,
  locale: LocaleArg = "en-US",
  currency = "USD",
  maximumFractionDigits = 0
): string {
  return new Intl.NumberFormat(locale, {
    style: "currency",
    currency,
    maximumFractionDigits,
  }).format(n);
}

export function formatPercent(n: number, fractionDigits = 1, locale: LocaleArg = "en-US"): string {
  return new Intl.NumberFormat(locale, {
    style: "percent",
    minimumFractionDigits: fractionDigits,
    maximumFractionDigits: fractionDigits,
  }).format(n);
}

export function formatDateTime(iso: string, locale: LocaleArg = "en-US"): string {
  return new Date(iso).toLocaleString(locale, {
    year: "numeric",
    month: "long",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function shortId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID().slice(0, 8);
  }
  return Math.random().toString(36).slice(2, 10);
}

/** Parse OCR/LLM amounts: `6000.00`, `6 000,00`, `1.234,56`, `1,234.56`, etc. */
export function parseNumericValue(raw: string): number | null {
  const text = raw.trim();
  if (!text || text === "—" || text === "-") return null;

  let cleaned = text.replace(/[^\d.,\s-]/g, "").replace(/\s/g, "");
  if (!cleaned || /^[.,-]+$/.test(cleaned)) return null;

  const lastComma = cleaned.lastIndexOf(",");
  const lastDot = cleaned.lastIndexOf(".");

  if (lastComma >= 0 && lastDot >= 0) {
    if (lastComma > lastDot) {
      cleaned = cleaned.replace(/\./g, "").replace(",", ".");
    } else {
      cleaned = cleaned.replace(/,/g, "");
    }
  } else if (lastComma >= 0) {
    const parts = cleaned.split(",");
    if (parts.length === 2 && parts[1].length <= 2) {
      cleaned = `${parts[0].replace(/\./g, "")}.${parts[1]}`;
    } else {
      cleaned = cleaned.replace(/,/g, "");
    }
  } else if (lastDot >= 0) {
    const parts = cleaned.split(".");
    if (parts.length === 2 && parts[1].length <= 2) {
      cleaned = `${parts[0].replace(/,/g, "")}.${parts[1]}`;
    } else {
      cleaned = cleaned.replace(/\./g, "");
    }
  }

  const num = Number(cleaned);
  return Number.isFinite(num) ? num : null;
}

export function formatExtractedFieldValue(
  value: string,
  type: string,
  locale: LocaleArg = "en-US"
): string {
  if (!value || value === "—") return "—";

  if (type === "currency" || type === "number") {
    const num = parseNumericValue(value);
    if (num === null) return value;
    if (type === "currency") {
      return new Intl.NumberFormat(locale, {
        style: "decimal",
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      }).format(num);
    }
    return new Intl.NumberFormat(locale).format(num);
  }

  if (type === "percent") {
    const num = parseNumericValue(value);
    if (num === null) return value;
    const ratio = value.includes("%") || Math.abs(num) > 1 ? num / 100 : num;
    return formatPercent(ratio, 0, locale);
  }

  return value;
}
