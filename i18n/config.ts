export const locales = ["en", "fr"] as const;
export type Locale = (typeof locales)[number];
export const defaultLocale: Locale = "en";
export const LOCALE_COOKIE = "wb_locale";

export function isLocale(value: string | undefined): value is Locale {
  return (locales as readonly string[]).includes(value ?? "");
}

/** The reader's IANA time zone, set by the browser, so server and client format dates alike. */
export const TIME_ZONE_COOKIE = "wb_tz";
