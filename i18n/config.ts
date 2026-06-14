export const locales = ["en", "fr"] as const;
export type Locale = (typeof locales)[number];
export const defaultLocale: Locale = "en";
export const LOCALE_COOKIE = "wb_locale";
export const THEME_COOKIE = "wb_theme";
export type Theme = "light" | "dark";
export const defaultTheme: Theme = "light";
