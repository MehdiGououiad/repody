const ONE_YEAR_SECONDS = 60 * 60 * 24 * 365;

/**
 * Persist a client-side UI preference (theme, locale) for a year.
 *
 * The modern `CookieStore` API that Biome prefers is still missing from Safari,
 * so this stays on `document.cookie` and is the single place that touches it.
 */
export function setPreferenceCookie(name: string, value: string): void {
  // biome-ignore lint/suspicious/noDocumentCookie: CookieStore lacks Safari support
  document.cookie = `${name}=${value}; path=/; max-age=${ONE_YEAR_SECONDS}; samesite=lax`;
}
