"use client";

import { Plus, Search } from "lucide-react";
import dynamic from "next/dynamic";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { UserMenu } from "@/components/auth/user-menu";
import { Kbd } from "@/components/ui/kbd";
import { isNavActive, MAIN_NAV_ITEMS } from "@/lib/navigation";
import { useBrand } from "@/lib/theme/brand-context";
import { cn } from "@/lib/utils";
import { BackendStatus } from "./backend-status";

const CommandPalette = dynamic(
  () => import("./command-palette").then((m) => ({ default: m.CommandPalette })),
  { ssr: false }
);

/** The brand: the client's logo when set, else a simple mark and the product name. */
export function BrandMark() {
  const brand = useBrand();
  if (brand.logoUrl) {
    // biome-ignore lint/performance/noImgElement: a client's logo comes from any URL.
    return <img src={brand.logoUrl} alt={brand.name} className="h-5 w-auto max-w-[140px]" />;
  }
  return (
    <span className="flex min-w-0 items-center gap-2">
      <span
        aria-hidden
        className="flex size-5 shrink-0 items-center justify-center rounded-sm bg-accent text-2xs font-semibold text-on-accent"
      >
        {brand.name.slice(0, 1).toUpperCase()}
      </span>
      <span className="truncate text-sm font-semibold text-ink">{brand.name}</span>
    </span>
  );
}

/** ⌘K or / opens the command palette from anywhere outside a text field. */
function useCommandPalette() {
  const [open, setOpen] = useState(false);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const typing =
        e.target instanceof HTMLInputElement ||
        e.target instanceof HTMLTextAreaElement ||
        (e.target instanceof HTMLElement && e.target.isContentEditable);
      if ((e.key === "k" && (e.metaKey || e.ctrlKey)) || (e.key === "/" && !typing)) {
        e.preventDefault();
        setOpen((v) => !v);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);
  return [open, setOpen] as const;
}

export function SidebarContent({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  const t = useTranslations("nav");
  const tBar = useTranslations("topbar");
  const [paletteOpen, setPaletteOpen] = useCommandPalette();

  return (
    <div className="flex h-full flex-col gap-4 px-2 py-3">
      <div className="flex h-7 items-center justify-between gap-2 ps-2">
        <BrandMark />
        <Link
          href="/workflows/new"
          onClick={onNavigate}
          aria-label={t("newWorkflow")}
          title={t("newWorkflow")}
          className="flex size-7 shrink-0 items-center justify-center rounded-md text-ink-3 transition-colors duration-100 hover:bg-hover hover:text-ink"
        >
          <Plus className="size-4" aria-hidden />
        </Link>
      </div>

      <button
        type="button"
        onClick={() => setPaletteOpen(true)}
        className="flex h-7 w-full cursor-pointer items-center gap-2 rounded-md px-2 text-sm text-ink-3 transition-colors duration-100 hover:bg-hover hover:text-ink-2"
      >
        <Search className="size-3.5 shrink-0" aria-hidden />
        <span className="flex-1 text-start">{tBar("search")}</span>
        <Kbd>⌘K</Kbd>
      </button>

      <nav className="flex flex-col gap-px" aria-label={t("main")}>
        {MAIN_NAV_ITEMS.map(({ href, labelKey, icon: Icon }) => {
          const active = isNavActive(pathname, href);
          return (
            <Link
              key={href}
              href={href}
              onClick={onNavigate}
              aria-current={active ? "page" : undefined}
              className={cn(
                "flex h-7 items-center gap-2 rounded-md px-2 text-sm font-medium transition-colors duration-100",
                active ? "bg-selected text-ink" : "text-ink-2 hover:bg-hover hover:text-ink"
              )}
            >
              <Icon
                className={cn("size-3.5 shrink-0", active ? "text-ink" : "text-ink-3")}
                strokeWidth={2}
                aria-hidden
              />
              {t(labelKey)}
            </Link>
          );
        })}
      </nav>

      <div className="mt-auto flex flex-col gap-1">
        <BackendStatus />
        <UserMenu />
      </div>

      {paletteOpen ? <CommandPalette open={paletteOpen} onOpenChange={setPaletteOpen} /> : null}
    </div>
  );
}

export function AppSidebar() {
  return (
    <aside className="hidden w-[232px] shrink-0 md:block">
      <SidebarContent />
    </aside>
  );
}
