import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import { NextIntlClientProvider } from "next-intl";
import { getLocale } from "next-intl/server";
import { Providers } from "@/components/providers/providers";
import { currentBrand } from "@/lib/theme/brand";
import { BrandProvider } from "@/lib/theme/brand-context";
import { themeStylesheet } from "@/lib/theme/generate";
import "./globals.css";

// Inter with its optical-size axis: the Display cut at heading sizes, the text cut below.
const inter = Inter({ subsets: ["latin"], axes: ["opsz"], variable: "--font-inter" });
const mono = JetBrains_Mono({ subsets: ["latin"], variable: "--font-mono-face" });

export function generateMetadata(): Metadata {
  const brand = currentBrand();
  return { title: { default: brand.name, template: `%s · ${brand.name}` } };
}

export default async function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  const locale = await getLocale();
  const brand = currentBrand();
  return (
    // next-themes sets the theme class before hydration, so <html> differs from the server render.
    <html lang={locale} suppressHydrationWarning className={`${inter.variable} ${mono.variable}`}>
      <head>
        {/* The brand's colour tokens, in the page from the first byte: no flash of another brand. */}
        <style>{themeStylesheet(brand, brand.radius)}</style>
      </head>
      <body className="min-h-dvh">
        <NextIntlClientProvider>
          <BrandProvider brand={{ name: brand.name, logoUrl: brand.logoUrl }}>
            <Providers>{children}</Providers>
          </BrandProvider>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
