"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import { useState } from "react";
import { LogOut, Plus, ShieldCheck, Menu, X } from "lucide-react";
import { Sheet, SheetContent, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useClientPathname } from "@/lib/hooks/use-client-pathname";
import { isNavActive, MAIN_NAV_ITEMS } from "@/lib/navigation";
import { SignOutButton } from "@/components/auth/sign-out-button";

export function MobileNav() {
  const pathname = useClientPathname();
  const t = useTranslations("nav");
  const tBrand = useTranslations("brand");
  const [open, setOpen] = useState(false);

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger asChild>
        <Button variant="ghost" size="icon" className="md:hidden" aria-label="Open menu">
          <Menu className="h-5 w-5" />
        </Button>
      </SheetTrigger>
      <SheetContent side="left" className="w-[260px] p-0 bg-sidebar text-sidebar-foreground border-r border-sidebar-border flex flex-col">
        <SheetTitle className="sr-only">Navigation</SheetTitle>
        <div className="px-6 py-6 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-lg bg-accent-blue/15 ring-1 ring-accent-blue/25 flex items-center justify-center text-accent-blue">
              <ShieldCheck className="h-5 w-5" aria-hidden="true" />
            </div>
            <div>
              <p className="font-display text-base font-semibold tracking-tight leading-none">{tBrand("name")}</p>
              <p className="text-[10px] uppercase tracking-[0.16em] text-sidebar-foreground/55 mt-1.5">
                {tBrand("tagline")}
              </p>
            </div>
          </div>
          <Button
            variant="ghost"
            size="icon"
            className="text-sidebar-foreground/70 hover:text-sidebar-foreground hover:bg-sidebar-accent"
            onClick={() => setOpen(false)}
            aria-label="Close menu"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>

        <div className="px-4 mb-4">
          <Link
            href="/workflows/new"
            onClick={() => setOpen(false)}
            className="w-full bg-accent-blue py-2.5 px-3 rounded-lg text-sm font-semibold flex items-center justify-center gap-2 hover:brightness-110 transition-[filter]"
            style={{ color: "var(--primary-stitch)" }}
          >
            <Plus className="h-4 w-4" aria-hidden="true" />
            {t("newWorkflow")}
          </Link>
        </div>

        <nav className="flex-1 flex flex-col gap-1 px-2" aria-label={tBrand("name")}>
          {MAIN_NAV_ITEMS.map(({ href, labelKey, icon: Icon }) => {
            const active = isNavActive(pathname, href);
            return (
              <Link
                key={href}
                href={href}
                onClick={() => setOpen(false)}
                className={cn(
                  "relative flex items-center gap-3 px-4 py-2.5 rounded-md text-sm font-medium transition-colors",
                  active
                    ? "bg-sidebar-accent text-sidebar-accent-foreground"
                    : "text-sidebar-foreground/70 hover:bg-sidebar-accent/50 hover:text-sidebar-foreground"
                )}
              >
                {active ? (
                  <span className="absolute left-0 top-1.5 bottom-1.5 w-[3px] rounded-r bg-accent-blue" />
                ) : null}
                <Icon className="h-4 w-4 shrink-0" aria-hidden="true" />
                <span>{t(labelKey)}</span>
              </Link>
            );
          })}
        </nav>

        <div className="mt-auto px-2 py-4 border-t border-sidebar-border">
          <SignOutButton
            className="w-full flex items-center gap-3 px-4 py-2.5 rounded-md text-sm font-medium text-sidebar-foreground/70 hover:bg-sidebar-accent/50 hover:text-sidebar-foreground transition-colors text-left disabled:opacity-50"
            onSignedOut={() => setOpen(false)}
          >
            <LogOut className="h-4 w-4" aria-hidden="true" />
            <span>{t("logout")}</span>
          </SignOutButton>
        </div>
      </SheetContent>
    </Sheet>
  );
}
