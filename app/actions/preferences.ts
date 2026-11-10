"use server";

import { revalidatePath } from "next/cache";
import { cookies } from "next/headers";
import { isLocale, LOCALE_COOKIE, type Locale, TIME_ZONE_COOKIE } from "@/i18n/config";

const ONE_YEAR = 60 * 60 * 24 * 365;

async function remember(name: string, value: string) {
  const store = await cookies();
  store.set(name, value, { path: "/", maxAge: ONE_YEAR, sameSite: "lax" });
  // Re-render every server component with the new preference.
  revalidatePath("/", "layout");
}

export async function setLocale(locale: Locale) {
  if (!isLocale(locale)) throw new Error(`Unsupported locale: ${locale}`);
  await remember(LOCALE_COOKIE, locale);
}

/** The browser's time zone, so the server formats dates as the reader's clock shows them. */
export async function setTimeZone(zone: string) {
  try {
    new Intl.DateTimeFormat("en", { timeZone: zone });
  } catch {
    throw new Error(`Unknown time zone: ${zone}`);
  }
  await remember(TIME_ZONE_COOKIE, zone);
}
