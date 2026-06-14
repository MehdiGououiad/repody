import type { Metadata } from "next";
import { JetBrains_Mono, Source_Sans_3 } from "next/font/google";
import { cookies } from "next/headers";
import { NextIntlClientProvider } from "next-intl";
import { getLocale, getMessages } from "next-intl/server";
import { ThemeProvider } from "@/components/providers/theme-provider";
import { QueryProvider } from "@/components/providers/query-provider";
import { Toaster } from "@/components/ui/sonner";
import { AppShell } from "@/components/layout/app-shell";
import { THEME_COOKIE, defaultTheme } from "@/i18n/config";
import type { Theme } from "@/i18n/config";
import "./globals.css";

const sourceSans = Source_Sans_3({
  subsets: ["latin"],
  variable: "--font-brand-sans",
  display: "swap",
  weight: ["400", "500", "600", "700"],
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jetbrains-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Repody",
  description: "Repody — enterprise document audit platform",
};

export default async function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  const [locale, messages, cookieStore] = await Promise.all([
    getLocale(),
    getMessages(),
    cookies(),
  ]);
  const rawTheme = cookieStore.get(THEME_COOKIE)?.value;
  const theme: Theme = rawTheme === "dark" || rawTheme === "light" ? rawTheme : defaultTheme;

  return (
    <html lang={locale} className={theme === "dark" ? "dark" : ""} style={{ colorScheme: theme }}>
      <body
        className={`${sourceSans.variable} ${jetbrainsMono.variable} antialiased min-h-dvh bg-background text-foreground`}
      >
        <NextIntlClientProvider locale={locale} messages={messages}>
          <ThemeProvider initialTheme={theme}>
            <QueryProvider>
              <AppShell>{children}</AppShell>
              <Toaster richColors closeButton position="bottom-right" />
            </QueryProvider>
          </ThemeProvider>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
