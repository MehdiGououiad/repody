import {
  FileCheck2,
  GitBranch,
  LayoutDashboard,
  Settings,
  Users,
  type LucideIcon,
} from "lucide-react";

export function isNavActive(pathname: string, href: string): boolean {
  return pathname === href || (href !== "/dashboard" && pathname.startsWith(href));
}

export type MainNavLabelKey = "dashboard" | "workflows" | "audits" | "users" | "settings";

export type MainNavItem = {
  href: string;
  labelKey: MainNavLabelKey;
  icon: LucideIcon;
};

export const MAIN_NAV_ITEMS: MainNavItem[] = [
  { href: "/dashboard", labelKey: "dashboard", icon: LayoutDashboard },
  { href: "/workflows", labelKey: "workflows", icon: GitBranch },
  { href: "/audits", labelKey: "audits", icon: FileCheck2 },
  { href: "/users", labelKey: "users", icon: Users },
  { href: "/settings", labelKey: "settings", icon: Settings },
];
