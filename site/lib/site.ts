/** Site-wide settings: change them here, every page follows. */
export const SITE = {
  name: "Repody",
  url: "https://repody.com",
  appUrl: "https://app.repody.com",
  /** The contact form posts access requests here (the app's API; CORS allows this site). */
  accessRequestsUrl: "https://app.repody.com/api/v1/access-requests",
  /** Cloudflare Turnstile's public site key (the widget repody-access-requests, repody.com). */
  turnstileSiteKey: "0x4AAAAAAGD9eQZHqJFQ2eSW",
  contactEmail: "contact@repody.com",
  /** The product video (HyperFrames): an MP4 or embed URL. Null shows the poster and a notice. */
  videoUrl: null as string | null,
} as const;

export const LOCALES = ["fr", "en"] as const;
export type Locale = (typeof LOCALES)[number];

/** Every page, by key; paths are the same in both languages, under /fr/ and /en/. */
export const PAGES = {
  home: "",
  platform: "platform",
  security: "security",
  architecture: "architecture",
  deployment: "deployment",
  engineering: "engineering",
  banks: "solutions/banks",
  insurance: "solutions/insurance",
  telecom: "solutions/telecom",
  contact: "contact",
  legal: "legal",
  privacy: "privacy",
} as const;
export type PageKey = keyof typeof PAGES;

export function href(locale: Locale, page: PageKey, hash?: string): string {
  const path = PAGES[page];
  return `/${locale}/${path ? `${path}/` : ""}${hash ? `#${hash}` : ""}`;
}

export function absolute(locale: Locale, page: PageKey): string {
  return `${SITE.url}${href(locale, page)}`;
}

export function isLocale(value: string): value is Locale {
  return (LOCALES as readonly string[]).includes(value);
}
