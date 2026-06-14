import { cookies, headers } from "next/headers";
import { getRequestConfig } from "next-intl/server";
import { defaultLocale, locales, LOCALE_COOKIE, type Locale } from "./config";

function negotiate(header: string | null): Locale {
  if (!header) return defaultLocale;
  for (const part of header.split(",")) {
    const tag = part.split(";")[0].trim().toLowerCase();
    const base = tag.split("-")[0] as Locale;
    if ((locales as readonly string[]).includes(base)) return base;
  }
  return defaultLocale;
}

export default getRequestConfig(async () => {
  const cookieStore = await cookies();
  const fromCookie = cookieStore.get(LOCALE_COOKIE)?.value;
  const headerList = await headers();
  const locale: Locale =
    fromCookie && (locales as readonly string[]).includes(fromCookie)
      ? (fromCookie as Locale)
      : negotiate(headerList.get("accept-language"));

  const messages = (await import(`../messages/${locale}.json`)).default;
  return { locale, messages };
});
