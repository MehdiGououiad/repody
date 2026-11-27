export type ModuleId = "idp" | "fraud" | "operator";

export type LicenseStatus = "active" | "grace" | "expired" | "invalid" | "unconfigured";

export type EntitlementState = {
  status: LicenseStatus;
  modules: readonly ModuleId[];
  warning?: string | null;
};

export type ModuleRouteTarget = {
  id: ModuleId;
  basePath: string;
};

export function isOperational(state: EntitlementState): boolean {
  return state.status === "active" || state.status === "grace";
}

export function hasModule(state: EntitlementState, module: ModuleId): boolean {
  return isOperational(state) && state.modules.includes(module);
}

export function showModuleSwitcher(state: EntitlementState): boolean {
  return isOperational(state) && state.modules.length >= 2;
}

/**
 * Single-module clients drop directly into their workspace (zero hub clutter);
 * multi-module clients land on `/hub` to launch owned agents and chain pipelines.
 */
export function resolveHomeRoute(
  state: EntitlementState,
  manifests: readonly ModuleRouteTarget[],
): string {
  const active = manifests.filter((manifest) => hasModule(state, manifest.id));
  const [only] = active;
  if (active.length === 1 && only) return only.basePath;
  if (active.length >= 2) return "/hub";
  return "/settings";
}
