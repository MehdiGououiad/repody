"use client";

import { Moon, Sun } from "lucide-react";
import { ThemeProvider, useTheme } from "next-themes";
import { useSyncExternalStore } from "react";

/** Light or dark: the reader's system until they choose, then their choice (next-themes keeps
 * it, and sets the class before paint, so the page never flashes the other theme). */
export function SiteTheme({ children }: { children: React.ReactNode }) {
  return (
    <ThemeProvider attribute="class" defaultTheme="system" enableSystem disableTransitionOnChange>
      {children}
    </ThemeProvider>
  );
}

const noop = () => () => {};

/** The header's switch between light and dark. */
export function ThemeToggle({ toLight, toDark }: { toLight: string; toDark: string }) {
  const { resolvedTheme, setTheme } = useTheme();
  // The theme is known only in the browser: the server renders a neutral button.
  const mounted = useSyncExternalStore(noop, () => true, () => false);
  const dark = mounted && resolvedTheme === "dark";
  const label = dark ? toLight : toDark;
  return (
    <button
      type="button"
      onClick={() => setTheme(dark ? "light" : "dark")}
      aria-label={label}
      title={label}
      className="flex size-8 items-center justify-center rounded-[4px] text-ink-3 transition-colors duration-100 hover:bg-hover hover:text-ink"
    >
      {dark ? <Sun className="size-4" aria-hidden /> : <Moon className="size-4" aria-hidden />}
    </button>
  );
}
