"use client";

import {
  Check,
  ChevronsUpDown,
  FileSearch,
  GitCompareArrows,
  Layers,
  ShieldAlert,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTranslations } from "next-intl";
import {
  Menu,
  MenuContent,
  MenuGroup,
  MenuGroupLabel,
  MenuItem,
  MenuSeparator,
  MenuTrigger,
} from "@/components/ui/menu";
import { cn } from "@/lib/utils";
import { useEntitlements, useHasModule, useShowModuleSwitcher } from "./entitlement-context";
import { resolveActiveWorkspace, type WorkspaceId } from "./manifests";

const WORKSPACE_META: Record<WorkspaceId, { labelKey: WorkspaceId; icon: typeof Layers }> = {
  hub: { labelKey: "hub", icon: Layers },
  idp: { labelKey: "idp", icon: FileSearch },
  fraud: { labelKey: "fraud", icon: ShieldAlert },
  cases: { labelKey: "cases", icon: GitCompareArrows },
};

/**
 * Adaptive switcher rendered in the sidebar ONLY when >=2 modules are licensed.
 * Single-module deployments return `null` so users never see unpurchased modules.
 */
export function WorkspaceSwitcher({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  const entitlements = useEntitlements();
  const showSwitcher = useShowModuleSwitcher();
  const hasIdp = useHasModule("idp");
  const hasFraud = useHasModule("fraud");
  const t = useTranslations("workspaces");

  if (!showSwitcher) return null;

  const active = resolveActiveWorkspace(pathname, entitlements);
  const current = WORKSPACE_META[active];
  const CurrentIcon = current.icon;

  return (
    <Menu>
      <MenuTrigger
        aria-label={t("switcherLabel")}
        className="flex h-8 w-full cursor-pointer items-center justify-between gap-2 rounded-md border border-line bg-raised px-2.5 text-[13px] font-medium text-ink shadow-[0_1px_2px_var(--shadow-color)] transition-colors hover:bg-hover focus-visible:outline-none focus-visible:shadow-[0_0_0_2px_var(--focus)]"
      >
        <span className="flex min-w-0 items-center gap-2">
          <CurrentIcon className="size-3.5 shrink-0 text-accent-ink" aria-hidden />
          <span className="truncate">{t(current.labelKey)}</span>
        </span>
        <ChevronsUpDown className="size-3.5 shrink-0 text-ink-3" aria-hidden />
      </MenuTrigger>
      <MenuContent align="start" sideOffset={6} className="w-[216px]">
        <MenuGroup>
          <MenuGroupLabel>{t("switcherLabel")}</MenuGroupLabel>
          <MenuItem render={<Link href="/hub" onClick={onNavigate} />}>
            <Layers className="size-3.5 text-ink-3" aria-hidden />
            <span className="flex-1">{t("hub")}</span>
            {active === "hub" ? <Check className="size-3.5 text-accent-ink" /> : null}
          </MenuItem>
          {hasIdp ? (
            <MenuItem render={<Link href="/dashboard" onClick={onNavigate} />}>
              <FileSearch className="size-3.5 text-ink-3" aria-hidden />
              <span className="flex-1">{t("idp")}</span>
              {active === "idp" ? <Check className="size-3.5 text-accent-ink" /> : null}
            </MenuItem>
          ) : null}
          {hasFraud ? (
            <MenuItem render={<Link href="/fraud" onClick={onNavigate} />}>
              <ShieldAlert className="size-3.5 text-ink-3" aria-hidden />
              <span className="flex-1">{t("fraud")}</span>
              {active === "fraud" ? <Check className="size-3.5 text-accent-ink" /> : null}
            </MenuItem>
          ) : null}
        </MenuGroup>
        <MenuSeparator />
        <MenuGroup>
          <MenuItem
            render={<Link href="/cases" onClick={onNavigate} />}
            className={cn(active === "cases" && "bg-selected")}
          >
            <GitCompareArrows className="size-3.5 text-ink-3" aria-hidden />
            <span className="flex-1">{t("cases")}</span>
            {active === "cases" ? <Check className="size-3.5 text-accent-ink" /> : null}
          </MenuItem>
        </MenuGroup>
      </MenuContent>
    </Menu>
  );
}
