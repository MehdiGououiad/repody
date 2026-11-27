import { hasModule, type EntitlementState, type ModuleId } from "./entitlements";

export type ModuleNavItem = {
  href: string;
  labelKey: string;
  permission?: string;
};

export type ModuleManifest = {
  id: ModuleId;
  labelKey: string;
  basePath: string;
  navItems: readonly ModuleNavItem[];
  casePanelId?: string;
};

export function createModuleRegistry(manifests: readonly ModuleManifest[]) {
  function listActive(state: EntitlementState): ModuleManifest[] {
    return manifests.filter((manifest) => hasModule(state, manifest.id));
  }

  function getActive(state: EntitlementState, id: ModuleId): ModuleManifest | undefined {
    return listActive(state).find((manifest) => manifest.id === id);
  }

  function activeNavItems(
    state: EntitlementState,
    permissions: readonly string[],
  ): Array<ModuleNavItem & { moduleId: ModuleId }> {
    const allowed = new Set(permissions);
    return listActive(state).flatMap((manifest) =>
      manifest.navItems
        .filter((item) => !item.permission || allowed.has(item.permission))
        .map((item) => ({ ...item, moduleId: manifest.id })),
    );
  }

  return { listActive, getActive, activeNavItems };
}
