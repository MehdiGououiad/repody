import type { Metadata } from "next";
import { absolute, LOCALES, type Locale, type PageKey, SITE } from "@/lib/site";

/** Title, description, canonical URL, language alternates and social cards for one page. */
export function pageMetadata(
  locale: Locale,
  page: PageKey,
  meta: { title: string; description: string },
): Metadata {
  const url = absolute(locale, page);
  return {
    title: page === "home" ? { absolute: meta.title } : meta.title,
    description: meta.description,
    alternates: {
      canonical: url,
      languages: {
        ...Object.fromEntries(LOCALES.map((l) => [l === "fr" ? "fr-MA" : "en", absolute(l, page)])),
        "x-default": absolute("fr", page),
      },
    },
    openGraph: {
      type: "website",
      url,
      siteName: SITE.name,
      title: meta.title,
      description: meta.description,
      locale: locale === "fr" ? "fr_MA" : "en_US",
      images: [{ url: `/og/${locale}.png`, width: 1200, height: 630, alt: meta.title }],
    },
    twitter: {
      card: "summary_large_image",
      title: meta.title,
      description: meta.description,
      images: [`/og/${locale}.png`],
    },
  };
}

/** Home > section > page, for search results. */
export function breadcrumb(locale: Locale, items: { name: string; page: PageKey }[]) {
  return {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: items.map((item, i) => ({
      "@type": "ListItem",
      position: i + 1,
      name: item.name,
      item: absolute(locale, item.page),
    })),
  };
}
