import type { Metadata, Viewport } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import { notFound } from "next/navigation";
import { JsonLd } from "@/components/json-ld";
import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";
import { dict } from "@/content";
import { isLocale, LOCALES, SITE } from "@/lib/site";
import { siteStylesheet } from "@/lib/theme";
import "../globals.css";

const inter = Inter({ subsets: ["latin"], axes: ["opsz"], variable: "--font-inter" });
const mono = JetBrains_Mono({ subsets: ["latin"], variable: "--font-mono-face" });

export const dynamicParams = false;

export function generateStaticParams() {
  return LOCALES.map((locale) => ({ locale }));
}

export const metadata: Metadata = {
  metadataBase: new URL(SITE.url),
  title: { default: SITE.name, template: `%s · ${SITE.name}` },
  icons: { icon: "/icon.svg" },
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#fbfaf9" },
    { media: "(prefers-color-scheme: dark)", color: "#1c1b1a" },
  ],
};

export default async function LocaleLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  if (!isLocale(locale)) notFound();
  const t = dict(locale);
  return (
    <html lang={locale === "fr" ? "fr-MA" : "en"} className={`${inter.variable} ${mono.variable}`}>
      <head>
        <style>{siteStylesheet()}</style>
      </head>
      <body>
        <JsonLd
          data={{
            "@context": "https://schema.org",
            "@type": "Organization",
            name: SITE.name,
            url: SITE.url,
            logo: `${SITE.url}/icon.svg`,
            email: SITE.contactEmail,
            areaServed: "MA",
            description: t.common.footer.tagline,
          }}
        />
        <SiteHeader locale={locale} t={t.common} />
        <main id="main">{children}</main>
        <SiteFooter locale={locale} t={t.common} />
      </body>
    </html>
  );
}
