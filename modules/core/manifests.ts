import { MAIN_NAV_ITEMS } from "@/lib/navigation";
import { hasModule, type EntitlementState, type ModuleId } from "./entitlements";
import type { ModuleManifest } from "./registry";

export type WorkspaceId = "hub" | "idp" | "fraud" | "cases";

const VALID_MODULES = new Set<ModuleId>(["idp", "fraud", "operator"]);

export const PLATFORM_MANIFESTS: readonly ModuleManifest[] = [
  {
    id: "idp",
    labelKey: "idp",
    basePath: "/dashboard",
    navItems: MAIN_NAV_ITEMS.filter((item) => item.href !== "/settings").map((item) => ({
      href: item.href,
      labelKey: item.labelKey,
      permission: item.permission,
    })),
    casePanelId: "idp",
  },
  {
    id: "fraud",
    labelKey: "fraud",
    basePath: "/fraud",
    navItems: [{ href: "/fraud", labelKey: "fraud" }],
    casePanelId: "fraud",
  },
];

export function parseEnvModules(raw: string | undefined): ModuleId[] {
  if (!raw?.trim()) return [];
  const unique: ModuleId[] = [];
  for (const part of raw.split(",")) {
    const candidate = part.trim().toLowerCase() as ModuleId;
    if (VALID_MODULES.has(candidate) && !unique.includes(candidate)) {
      unique.push(candidate);
    }
  }
  return unique;
}

export function resolveActiveWorkspace(pathname: string, state: EntitlementState): WorkspaceId {
  if (pathname === "/hub" || pathname.startsWith("/hub/")) return "hub";
  if (pathname === "/fraud" || pathname.startsWith("/fraud/")) return "fraud";
  if (pathname === "/cases" || pathname.startsWith("/cases/")) return "cases";
  if (hasModule(state, "idp")) return "idp";
  if (hasModule(state, "fraud")) return "fraud";
  return "idp";
}
