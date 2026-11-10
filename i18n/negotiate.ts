import { match } from "@formatjs/intl-localematcher";
import Negotiator from "negotiator";
import { defaultLocale, type Locale, locales } from "./config";

/** The best supported locale for an Accept-Language header (RFC 4647 lookup). A missing or
 * wildcard-only header, or one with malformed tags, gets the default locale. */
export function negotiateLocale(acceptLanguage: string | null): Locale {
  const requested = new Negotiator({ headers: { "accept-language": acceptLanguage ?? "" } })
    .languages()
    .filter((tag) => tag !== "*");
  try {
    return match(requested, locales, defaultLocale) as Locale;
  } catch {
    return defaultLocale;
  }
}

/** The time zone if the runtime knows it, else UTC. */
export function validTimeZone(zone: string | undefined): string {
  try {
    return zone
      ? new Intl.DateTimeFormat("en", { timeZone: zone }).resolvedOptions().timeZone
      : "UTC";
  } catch {
    return "UTC";
  }
}
