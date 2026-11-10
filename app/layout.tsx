import type { Metadata } from "next";
import { NextIntlClientProvider } from "next-intl";
import { getLocale } from "next-intl/server";
import { Providers } from "@/components/providers/providers";
import { Toaster } from "@/components/ui/sonner";
import "./globals.css";

export const metadata: Metadata = {
  title: "Repody",
  description: "Repody — enterprise document audit platform",
};

export default async function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  const locale = await getLocale();
  return (
    // next-themes sets the theme class before hydration, so <html> differs from the server render.
    <html lang={locale} suppressHydrationWarning>
      <body className="antialiased min-h-dvh bg-background text-foreground">
        <NextIntlClientProvider>
          <Providers>
            {children}
            <Toaster richColors closeButton position="bottom-right" />
          </Providers>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
