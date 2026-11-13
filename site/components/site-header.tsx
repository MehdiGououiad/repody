"use client";

import { Menu, X } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { ThemeToggle } from "@/components/theme-toggle";
import type { Dict } from "@/content";
import { href, type Locale, type PageKey, SITE } from "@/lib/site";

const NAV: PageKey[] = ["platform", "security", "architecture", "deployment", "engineering"];
const SOLUTIONS: PageKey[] = ["banks", "insurance", "telecom"];

export function Logo({ locale }: { locale: Locale }) {
  return (
    <Link href={href(locale, "home")} className="flex items-center gap-2" aria-label="Repody">
      <span className="flex size-6 items-center justify-center rounded-md bg-accent text-xs font-semibold text-on-accent">
        R
      </span>
      <span className="text-[0.9375rem] font-semibold text-ink">Repody</span>
    </Link>
  );
}

export function SiteHeader({ locale, t }: { locale: Locale; t: Dict["common"] }) {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const other: Locale = locale === "fr" ? "en" : "fr";
  const otherPath = pathname.replace(/^\/(fr|en)(?=\/|$)/, `/${other}`);
  const label = (key: PageKey) => t.nav[key as keyof typeof t.nav];
  const current = (key: PageKey) => pathname === href(locale, key);

  useEffect(() => setOpen(false), [pathname]);

  const link =
    "rounded-md px-2.5 py-1.5 text-sm text-ink-2 transition-colors duration-100 hover:bg-hover hover:text-ink aria-[current=page]:text-ink";

  return (
    <header className="sticky top-0 z-40 border-b border-line bg-panel">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:start-3 focus:top-3 focus:rounded-md focus:bg-overlay focus:px-3 focus:py-2 focus:text-sm focus:shadow-pop"
      >
        {t.skip}
      </a>
      <div className="mx-auto flex h-14 w-full max-w-[1180px] items-center gap-4 px-5 md:px-8">
        <Logo locale={locale} />
        <nav className="ms-4 hidden items-center gap-0.5 lg:flex" aria-label="Repody">
          {NAV.map((key) => (
            <Link
              key={key}
              href={href(locale, key)}
              className={link}
              aria-current={current(key) ? "page" : undefined}
            >
              {label(key)}
            </Link>
          ))}
          <details className="group relative">
            <summary
              className={`${link} flex cursor-pointer list-none items-center gap-1 [&::-webkit-details-marker]:hidden`}
            >
              {t.nav.solutions}
            </summary>
            <div className="absolute start-0 top-full mt-1 flex w-48 flex-col rounded-lg bg-overlay p-1 shadow-pop">
              {SOLUTIONS.map((key) => (
                <Link
                  key={key}
                  href={href(locale, key)}
                  className={link}
                  aria-current={current(key) ? "page" : undefined}
                >
                  {label(key)}
                </Link>
              ))}
            </div>
          </details>
        </nav>
        <div className="ms-auto flex items-center gap-1">
          <Link
            href={otherPath}
            hrefLang={other}
            className={`${link} uppercase`}
            aria-label={t.language}
          >
            {other}
          </Link>
          <ThemeToggle toLight={t.toLight} toDark={t.toDark} />
          <a
            href={SITE.playgroundUrl}
            className="hidden h-8 items-center rounded-[4px] px-3 text-sm font-medium text-ink shadow-[0_0_0_1px_var(--line-strong)] transition-colors duration-100 hover:bg-hover md:inline-flex"
          >
            {t.playgroundShort}
          </a>
          <Link
            href={href(locale, "contact")}
            className="hidden h-8 items-center rounded-[4px] bg-ink px-3 text-sm font-medium text-panel transition-colors duration-100 hover:bg-ink-2 sm:inline-flex"
          >
            {t.demo}
          </Link>
          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            aria-expanded={open}
            aria-controls="mobile-menu"
            aria-label={open ? t.close : t.menu}
            className="flex size-9 items-center justify-center rounded-md text-ink-2 hover:bg-hover lg:hidden"
          >
            {open ? <X className="size-5" /> : <Menu className="size-5" />}
          </button>
        </div>
      </div>
      {open ? (
        <nav
          id="mobile-menu"
          className="border-t border-line bg-panel px-5 pb-5 pt-2 lg:hidden"
          aria-label="Repody"
        >
          {[...NAV, ...SOLUTIONS].map((key) => (
            <Link
              key={key}
              href={href(locale, key)}
              className="flex h-11 items-center border-b border-line text-[0.9375rem] text-ink"
            >
              {label(key)}
            </Link>
          ))}
          <Link
            href={href(locale, "contact")}
            className="mt-4 flex h-11 items-center justify-center rounded-[4px] bg-ink text-[0.9375rem] font-medium text-panel"
          >
            {t.demo}
          </Link>
          <a
            href={SITE.playgroundUrl}
            className="mt-2 flex h-11 items-center justify-center rounded-[4px] text-[0.9375rem] font-medium text-ink shadow-[0_0_0_1px_var(--line-strong)]"
          >
            {t.playground}
          </a>
        </nav>
      ) : null}
    </header>
  );
}
