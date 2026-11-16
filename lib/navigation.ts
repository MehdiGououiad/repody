import {
  Activity,
  FileCheck2,
  GitBranch,
  LayoutDashboard,
  type LucideIcon,
  Settings,
  ShieldCheck,
} from "lucide-react";
import type { Permission } from "@/lib/types";

export function isNavActive(pathname: string, href: string): boolean {
  return pathname === href || (href !== "/dashboard" && pathname.startsWith(href));
}

export type MainNavLabelKey =
  | "dashboard"
  | "operations"
  | "workflows"
  | "audits"
  | "admin"
  | "settings";

export type MainNavItem = {
  href: string;
  labelKey: MainNavLabelKey;
  icon: LucideIcon;
  /** Shown only to callers with it; Settings is for everyone (it shows your access). */
  permission?: Permission;
};

export const MAIN_NAV_ITEMS: MainNavItem[] = [
  { href: "/dashboard", labelKey: "dashboard", icon: LayoutDashboard, permission: "metrics:read" },
  { href: "/operations", labelKey: "operations", icon: Activity, permission: "run:read" },
  { href: "/workflows", labelKey: "workflows", icon: GitBranch, permission: "workflow:read" },
  { href: "/audits", labelKey: "audits", icon: FileCheck2, permission: "run:read" },
  { href: "/admin", labelKey: "admin", icon: ShieldCheck, permission: "clients:manage" },
  { href: "/settings", labelKey: "settings", icon: Settings },
];
