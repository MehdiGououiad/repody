import { cookies, headers } from "next/headers";
import { getRequestConfig } from "next-intl/server";
import { isLocale, LOCALE_COOKIE, TIME_ZONE_COOKIE } from "./config";
import { negotiateLocale, validTimeZone } from "./negotiate";

/** The locale chosen in the language menu (a cookie), else the browser's preference; dates in
 * the reader's time zone (UTC until the browser has reported it). */
export default getRequestConfig(async () => {
  const [cookieStore, headerList] = await Promise.all([cookies(), headers()]);
  const chosen = cookieStore.get(LOCALE_COOKIE)?.value;
  const locale = isLocale(chosen) ? chosen : negotiateLocale(headerList.get("accept-language"));
  return {
    locale,
    timeZone: validTimeZone(cookieStore.get(TIME_ZONE_COOKIE)?.value),
    messages: (await import(`../messages/${locale}.json`)).default,
  };
});
