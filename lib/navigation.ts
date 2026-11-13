import {
  Activity,
  FileCheck2,
  GitBranch,
  LayoutDashboard,
  type LucideIcon,
  Settings,
} from "lucide-react";

export function isNavActive(pathname: string, href: string): boolean {
  return pathname === href || (href !== "/dashboard" && pathname.startsWith(href));
}

export type MainNavLabelKey = "dashboard" | "operations" | "workflows" | "audits" | "settings";

export type MainNavItem = {
  href: string;
  labelKey: MainNavLabelKey;
  icon: LucideIcon;
};

export const MAIN_NAV_ITEMS: MainNavItem[] = [
  { href: "/dashboard", labelKey: "dashboard", icon: LayoutDashboard },
  { href: "/operations", labelKey: "operations", icon: Activity },
  { href: "/workflows", labelKey: "workflows", icon: GitBranch },
  { href: "/audits", labelKey: "audits", icon: FileCheck2 },
  { href: "/settings", labelKey: "settings", icon: Settings },
];
