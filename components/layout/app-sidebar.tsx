"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import {
  LayoutDashboard,
  GitBranch,
  FileCheck2,
  SlidersHorizontal,
  BookOpen,
  LogOut,
  Plus,
  ShieldCheck,
} from "lucide-react";
import { cn } from "@/lib/utils";

const navItems = [
  { href: "/dashboard", labelKey: "dashboard", icon: LayoutDashboard },
  { href: "/workflows", labelKey: "workflows", icon: GitBranch },
  { href: "/audits", labelKey: "audits", icon: FileCheck2 },
  { href: "/settings", labelKey: "settings", icon: SlidersHorizontal },
] as const;

export function AppSidebar() {
  const pathname = usePathname();
  const t = useTranslations("nav");
  const tBrand = useTranslations("brand");

  return (
    <aside className="hidden md:flex fixed left-0 top-0 z-40 h-screen w-[248px] flex-col bg-sidebar text-sidebar-foreground border-r border-sidebar-border py-6 overflow-hidden">
      <div
        className="pointer-events-none absolute inset-0 opacity-30"
        aria-hidden
        style={{
          background:
            "radial-gradient(ellipse 120% 80% at -20% 0%, rgba(196,163,90,0.18), transparent 55%)",
        }}
      />

      <div className="relative px-6 mb-8 flex items-center gap-3">
        <div className="h-10 w-10 rounded-lg bg-accent-blue/15 ring-1 ring-accent-blue/25 flex items-center justify-center text-accent-blue shadow-[0_0_24px_-6px_var(--accent-blue-glow)]">
          <ShieldCheck className="h-5 w-5" aria-hidden="true" />
        </div>
        <div>
          <p className="font-display text-xl font-semibold tracking-tight leading-none">
            {tBrand("name")}
          </p>
          <p className="text-[10px] uppercase tracking-[0.16em] text-sidebar-foreground/55 mt-1.5">
            {tBrand("tagline")}
          </p>
        </div>
      </div>

      <div className="relative px-4 mb-6">
        <Link
          href="/workflows/new"
          className="group w-full bg-accent-blue text-primary-stitch py-2.5 px-3 rounded-lg text-sm font-semibold flex items-center justify-center gap-2 hover:brightness-110 transition-[filter,box-shadow] shadow-[0_8px_24px_-12px_var(--accent-blue-glow)]"
          style={{ color: "var(--primary-stitch)" }}
        >
          <Plus className="h-4 w-4 transition-transform group-hover:rotate-90 duration-300" aria-hidden="true" />
          {t("newWorkflow")}
        </Link>
      </div>

      <nav className="relative flex-1 flex flex-col gap-0.5 px-2" aria-label={tBrand("name")}>
        {navItems.map(({ href, labelKey, icon: Icon }) => {
          const active =
            pathname === href ||
            (href !== "/dashboard" && pathname.startsWith(href));
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "relative flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-[background-color,color,transform] duration-200",
                active
                  ? "bg-sidebar-accent text-sidebar-accent-foreground shadow-inner"
                  : "text-sidebar-foreground/65 hover:bg-sidebar-accent/45 hover:text-sidebar-foreground hover:translate-x-0.5"
              )}
            >
              {active ? (
                <span className="absolute left-0 top-2 bottom-2 w-[3px] rounded-r bg-accent-blue shadow-[0_0_12px_var(--accent-blue-glow)]" />
              ) : null}
              <Icon className={cn("h-4 w-4 shrink-0", active && "text-accent-blue")} aria-hidden="true" />
              <span>{t(labelKey)}</span>
            </Link>
          );
        })}
      </nav>

      <div className="relative mt-auto px-2 pt-4 border-t border-sidebar-border/80">
        <Link
          href="/settings?tab=diagnostics"
          className="flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium text-sidebar-foreground/55 hover:bg-sidebar-accent/45 hover:text-sidebar-foreground transition-colors"
        >
          <BookOpen className="h-4 w-4" aria-hidden="true" />
          <span>{t("documentation")}</span>
        </Link>
        <button
          type="button"
          onClick={() => toast.message(t("logout"), { description: "Coming soon." })}
          className="w-full flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium text-sidebar-foreground/55 hover:bg-sidebar-accent/45 hover:text-sidebar-foreground transition-colors text-left"
        >
          <LogOut className="h-4 w-4" aria-hidden="true" />
          <span>{t("logout")}</span>
        </button>
      </div>
    </aside>
  );
}
