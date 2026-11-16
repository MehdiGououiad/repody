"use client";

import { useShortcut, useShortcutHint } from "@ui-sdk/react/shortcuts";
import { PanelLeft, Plus, Search } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTranslations } from "next-intl";
import { useState } from "react";
import { useCan, useNavItems } from "@/components/auth/access-context";
import { UserMenu } from "@/components/auth/user-menu";
import { Button } from "@/components/ui/button";
import { Kbd } from "@/components/ui/kbd";
import { StatusGlyph } from "@/components/ui/status-glyph";
import { Tooltip } from "@/components/ui/tooltip";
import { $api } from "@/lib/api/browser";
import { reviewCount } from "@/lib/audits/review";
import { isNavActive } from "@/lib/navigation";
import { useBrand } from "@/lib/theme/brand-context";
import { cn } from "@/lib/utils";
import { BackendStatus } from "./backend-status";
import { openCommandPalette } from "./command-palette";

const LIVE_MS = 15_000;

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
        className="flex size-5 shrink-0 items-center justify-center rounded-[5px] bg-accent text-2xs font-semibold text-on-accent shadow-[inset_0_1px_0_oklch(1_0_0/0.2)]"
      >
        {brand.name.slice(0, 1).toUpperCase()}
      </span>
      <span className="truncate text-[13px] font-semibold text-ink">{brand.name}</span>
    </span>
  );
}

/** A live count beside a nav item; ticks when it changes. */
function Count({ value, tone = "neutral" }: { value: number; tone?: "neutral" | "fail" }) {
  if (!value) return null;
  return (
    <AnimatePresence mode="popLayout" initial={false}>
      <motion.span
        key={value}
        initial={{ y: -6, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        exit={{ y: 6, opacity: 0 }}
        transition={{ duration: 0.2, ease: [0.23, 1, 0.32, 1] }}
        className={cn(
          "ms-auto inline-flex h-4 min-w-4 items-center justify-center rounded-full px-1 text-2xs font-semibold tabular-nums",
          tone === "fail" ? "bg-fail-wash text-fail-ink" : "bg-selected text-ink-2"
        )}
      >
        {value}
      </motion.span>
    </AnimatePresence>
  );
}

const navRow =
  "group flex h-7 items-center gap-2 rounded-md px-2 text-[13px] font-medium transition-colors duration-100";

export function SidebarContent({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  const t = useTranslations("nav");
  const tShell = useTranslations("shell");
  const searchHint = useShortcutHint("mod+k");
  // Its own cache entry (`{}`, not the page's `undefined`): the layout renders before the
  // dashboard page's HydrationBoundary, and a shared entry created here would keep the page's
  // streamed prefetch from hydrating (its Suspense query then fails on the server).
  const navItems = useNavItems();
  const canCreate = useCan("workflow:write");
  const dashboard = $api.useQuery(
    "get",
    "/v1/dashboard",
    {},
    { refetchInterval: LIVE_MS, enabled: useCan("metrics:read") }
  ).data;
  const toReview = dashboard ? reviewCount(dashboard.performanceSeries) : 0;
  const running = (dashboard?.queue.runningRuns ?? 0) + (dashboard?.queue.queuedRuns ?? 0);
  const recent = (dashboard?.workflows ?? []).slice(0, 5);

  return (
    <div className="flex h-full flex-col gap-3 px-2 py-2.5">
      <div className="flex h-7 items-center justify-between gap-2 ps-1.5">
        <BrandMark />
        {canCreate ? (
          <Tooltip label={tShell("create")} shortcut="C">
            <Link
              href="/workflows/new"
              onClick={onNavigate}
              aria-label={t("newWorkflow")}
              className="flex size-7 shrink-0 items-center justify-center rounded-md bg-raised text-ink-2 shadow-[0_0_0_1px_var(--line)] transition-colors duration-100 hover:bg-hover hover:text-ink"
            >
              <Plus className="size-3.5" aria-hidden />
            </Link>
          </Tooltip>
        ) : null}
      </div>

      <Button
        variant="ghost"
        onClick={openCommandPalette}
        className="w-full justify-start gap-2 px-2 font-normal text-ink-3"
      >
        <Search className="size-3.5 shrink-0" aria-hidden />
        <span className="flex-1 text-start">{tShell("search")}</span>
        <Kbd>{searchHint.text}</Kbd>
      </Button>

      <nav className="flex flex-col gap-px" aria-label={t("main")}>
        {navItems.map(({ href, labelKey, icon: Icon }) => {
          const active = isNavActive(pathname, href);
          return (
            <Link
              key={href}
              href={href}
              onClick={onNavigate}
              aria-current={active ? "page" : undefined}
              className={cn(
                navRow,
                active ? "bg-selected text-ink" : "text-ink-2 hover:bg-hover hover:text-ink"
              )}
            >
              <Icon
                className={cn("size-3.5 shrink-0", active ? "text-ink" : "text-ink-3")}
                strokeWidth={2}
                aria-hidden
              />
              <span className="truncate">{t(labelKey)}</span>
              {labelKey === "dashboard" ? <Count value={toReview} tone="fail" /> : null}
              {labelKey === "operations" && running ? (
                <span
                  className="ms-auto flex shrink-0 items-center gap-1.5 text-2xs font-semibold tabular-nums text-accent-ink"
                  title={tShell("running", { count: running })}
                >
                  <span className="relative flex size-1.5">
                    <span className="absolute inset-0 animate-ping rounded-full bg-accent opacity-60 motion-reduce:hidden" />
                    <span className="relative size-1.5 rounded-full bg-accent" />
                  </span>
                  {running}
                </span>
              ) : null}
            </Link>
          );
        })}
      </nav>

      {recent.length ? (
        <div className="flex min-h-0 flex-col gap-px">
          <p className="px-2 pb-1 text-xs font-medium text-ink-4">{tShell("recentWorkflows")}</p>
          {recent.map((workflow) => {
            const href = `/workflows/${workflow.id}/edit`;
            const active = pathname.startsWith(`/workflows/${workflow.id}`);
            return (
              <Link
                key={workflow.id}
                href={href}
                onClick={onNavigate}
                className={cn(
                  navRow,
                  "font-normal",
                  active ? "bg-selected text-ink" : "text-ink-2 hover:bg-hover hover:text-ink"
                )}
              >
                <StatusGlyph status={workflow.status === "active" ? "live" : "draft"} />
                <span className="truncate">{workflow.name}</span>
                {workflow.totalRuns ? (
                  <span className="ms-auto text-2xs tabular-nums text-ink-4">
                    {Math.round(workflow.successRate * 100)}%
                  </span>
                ) : null}
              </Link>
            );
          })}
        </div>
      ) : null}

      <div className="mt-auto flex flex-col gap-1">
        <BackendStatus />
        <UserMenu />
      </div>
    </div>
  );
}

export function AppSidebar() {
  const tShell = useTranslations("shell");
  const [collapsed, setCollapsed] = useState(false);
  useShortcut("[", () => setCollapsed((value) => !value), { description: tShell("collapse") });
  return (
    <>
      <motion.aside
        initial={false}
        animate={{ width: collapsed ? 0 : 224, opacity: collapsed ? 0 : 1 }}
        transition={{ duration: 0.2, ease: [0.23, 1, 0.32, 1] }}
        className="hidden shrink-0 overflow-hidden md:block"
        aria-hidden={collapsed || undefined}
        inert={collapsed || undefined}
      >
        <div className="h-full w-[224px]">
          <SidebarContent />
        </div>
      </motion.aside>
      {collapsed ? (
        <Tooltip label={tShell("expand")} shortcut="[" side="right">
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={() => setCollapsed(false)}
            aria-label={tShell("expand")}
            className="fixed start-2.5 top-2.5 z-30 hidden size-7 cursor-pointer items-center justify-center rounded-md text-ink-3 hover:bg-hover hover:text-ink md:flex"
          >
            <PanelLeft className="size-3.5" aria-hidden />
          </Button>
        </Tooltip>
      ) : null}
    </>
  );
}
