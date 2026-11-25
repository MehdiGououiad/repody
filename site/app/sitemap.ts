import type { MetadataRoute } from "next";
import { absolute, LOCALES, PAGES, type PageKey } from "@/lib/site";

export const dynamic = "force-static";

/** Every page in both languages, each with its alternates. */
export default function sitemap(): MetadataRoute.Sitemap {
  const pages = Object.keys(PAGES) as PageKey[];
  return pages.flatMap((page) =>
    LOCALES.map((locale) => ({
      url: absolute(locale, page),
      changeFrequency: "monthly" as const,
      priority: page === "home" ? 1 : page === "legal" || page === "privacy" ? 0.2 : 0.8,
      alternates: {
        languages: {
          "fr-MA": absolute("fr", page),
          en: absolute("en", page),
          "x-default": absolute("fr", page),
        },
      },
    })),
  );
}
