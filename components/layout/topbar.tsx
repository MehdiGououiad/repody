"use client";

import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { useTranslations } from "next-intl";
import { Bell, HelpCircle, History, Search, Sun, Moon } from "lucide-react";
import { toast } from "sonner";
import { useTheme } from "@/components/providers/theme-provider";
import { MobileNav } from "./mobile-nav";
import { Button } from "@/components/ui/button";
import { LanguageSwitcher } from "./language-switcher";
import { BackendStatus } from "./backend-status";

const CommandPalette = dynamic(
  () =>
    import("./command-palette").then((m) => ({ default: m.CommandPalette })),
  { ssr: false }
);

export function TopBar() {
  const tBar = useTranslations("topbar");
  const { theme, toggleTheme } = useTheme();
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.key === "k" && (e.metaKey || e.ctrlKey)) || e.key === "/") {
        if (
          e.target instanceof HTMLInputElement ||
          e.target instanceof HTMLTextAreaElement
        ) {
          return;
        }
        e.preventDefault();
        setOpen((v) => !v);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  return (
    <header className="sticky top-0 z-30 h-16 w-full min-w-0 overflow-hidden border-b border-border/80 bg-card/75 backdrop-blur-md supports-[backdrop-filter]:bg-card/60 flex items-center justify-between px-2 sm:px-4 md:px-6">
      <div className="flex shrink-0 items-center gap-1 sm:gap-2 md:gap-4">
        <MobileNav />
        <button
          type="button"
          onClick={() => setOpen(true)}
          aria-label={tBar("searchPlaceholder")}
          className="hidden md:flex cursor-pointer items-center gap-2 min-h-11 h-11 w-80 rounded-lg border border-input/80 bg-surface/80 px-3 text-sm text-muted-foreground hover:border-accent-blue/40 hover:bg-surface-container-low active:scale-[0.99] transition-[border-color,background-color,transform] duration-200"
        >
          <Search className="h-4 w-4 text-accent-blue/70" aria-hidden="true" />
          <span>{tBar("searchPlaceholder")}</span>
          <kbd className="ml-auto text-[10px] font-mono bg-surface-container-high/80 px-1.5 py-0.5 rounded border border-border/60">
            {"⌘\u00a0K"}
          </kbd>
        </button>
        <button
          type="button"
          onClick={() => setOpen(true)}
          className="md:hidden flex cursor-pointer items-center justify-center min-h-11 min-w-11 h-11 w-11 rounded-lg border border-input bg-surface text-muted-foreground hover:bg-muted/50 active:scale-[0.98] transition-[background-color,transform] duration-200"
          aria-label={tBar("searchPlaceholder")}
        >
          <Search className="h-4 w-4" aria-hidden="true" />
        </button>
      </div>

      <div className="flex min-w-0 items-center justify-end gap-0.5 sm:gap-2">
        <span className="hidden lg:inline-flex">
          <BackendStatus />
        </span>
        <LanguageSwitcher />
        <Button
          variant="ghost"
          size="icon"
          onClick={toggleTheme}
          aria-label={tBar("toggleTheme")}
        >
          {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
        </Button>
        <Button
          variant="ghost"
          size="icon"
          className="relative"
          aria-label={tBar("notifications")}
          onClick={() =>
            toast.message(tBar("notifications"), { description: "Coming soon." })
          }
        >
          <Bell className="h-4 w-4" />
          <span className="absolute top-2 right-2 h-1.5 w-1.5 rounded-full bg-accent-blue ring-2 ring-card" aria-hidden="true" />
        </Button>
        <Button
          variant="ghost"
          size="icon"
          className="hidden sm:inline-flex"
          aria-label={tBar("help")}
          onClick={() => toast.message(tBar("help"), { description: "Coming soon." })}
        >
          <HelpCircle className="h-4 w-4" />
        </Button>
        <Button
          variant="ghost"
          size="icon"
          className="hidden sm:inline-flex"
          aria-label={tBar("history")}
          onClick={() => toast.message(tBar("history"), { description: "Coming soon." })}
        >
          <History className="h-4 w-4" />
        </Button>
        <div
          className="ml-1 hidden size-8 rounded-full bg-gradient-to-br from-accent-blue/30 to-sidebar-accent text-on-surface sm:flex items-center justify-center text-xs font-semibold ring-1 ring-accent-blue/30"
          aria-label={tBar("accountInitials")}
          role="img"
        >
          MA
        </div>
      </div>

      {open ? <CommandPalette open={open} onOpenChange={setOpen} /> : null}
    </header>
  );
}
