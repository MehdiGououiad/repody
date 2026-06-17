import type { Metadata } from "next";
import { cookies } from "next/headers";
import { NextIntlClientProvider } from "next-intl";
import { getLocale, getMessages } from "next-intl/server";
import { ThemeProvider } from "@/components/providers/theme-provider";
import { QueryProvider } from "@/components/providers/query-provider";
import { Toaster } from "@/components/ui/sonner";
import { AppShell } from "@/components/layout/app-shell";
import { AuthSessionProvider } from "@/components/providers/session-provider";
import { THEME_COOKIE, defaultTheme } from "@/i18n/config";
import type { Theme } from "@/i18n/config";
import "./globals.css";

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
      <body className="antialiased min-h-dvh bg-background text-foreground">
        <NextIntlClientProvider locale={locale} messages={messages}>
          <ThemeProvider initialTheme={theme}>
            <QueryProvider>
              <AuthSessionProvider>
                <AppShell>{children}</AppShell>
                <Toaster richColors closeButton position="bottom-right" />
              </AuthSessionProvider>
            </QueryProvider>
          </ThemeProvider>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
