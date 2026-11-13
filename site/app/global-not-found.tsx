import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { ButtonLink } from "@/components/ui";
import { siteStylesheet } from "@/lib/theme";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], axes: ["opsz"], variable: "--font-inter" });

export const metadata: Metadata = { title: "404 · Repody", robots: { index: false } };

/** Any unknown address, in both languages: the reader's language is not known here. */
export default function GlobalNotFound() {
  return (
    <html lang="fr" className={inter.variable}>
      <head>
        <style>{siteStylesheet()}</style>
      </head>
      <body>
        <main className="mx-auto flex min-h-dvh max-w-[640px] flex-col justify-center gap-6 px-5">
          <p className="font-mono text-sm text-ink-4">404</p>
          <h1 className="text-headline font-semibold text-ink">
            Cette page n'existe pas.
            <span className="block text-ink-3">This page does not exist.</span>
          </h1>
          <div className="flex flex-wrap gap-3">
            <ButtonLink href="/fr/">Accueil</ButtonLink>
            <ButtonLink href="/en/" variant="secondary">
              Home
            </ButtonLink>
          </div>
        </main>
      </body>
    </html>
  );
}
