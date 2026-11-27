import { describe, expect, test } from "bun:test";
import type { EntitlementState } from "./entitlements";
import { createModuleRegistry, type ModuleManifest } from "./registry";

const MANIFESTS: readonly ModuleManifest[] = [
  {
    id: "idp",
    labelKey: "modules.idp",
    basePath: "/idp",
    casePanelId: "idp-fields",
    navItems: [
      { href: "/idp/workflows", labelKey: "nav.workflows", permission: "workflow:read" },
      { href: "/idp/audits", labelKey: "nav.audits", permission: "run:read" },
    ],
  },
  {
    id: "fraud",
    labelKey: "modules.fraud",
    basePath: "/fraud",
    casePanelId: "fraud-evidence",
    navItems: [{ href: "/fraud/analyses", labelKey: "nav.analyses", permission: "fraud:read" }],
  },
];

describe("module registry", () => {
  test("hides unpurchased modules and filters nav items by RBAC permissions", () => {
    const registry = createModuleRegistry(MANIFESTS);
    const fraudOnly: EntitlementState = { status: "active", modules: ["fraud"] };

    expect(registry.listActive(fraudOnly).map((m) => m.id)).toEqual(["fraud"]);
    expect(registry.getActive(fraudOnly, "idp")).toBeUndefined();
    expect(registry.getActive(fraudOnly, "fraud")?.casePanelId).toBe("fraud-evidence");

    expect(registry.activeNavItems(fraudOnly, ["workflow:read", "fraud:read"])).toEqual([
      {
        moduleId: "fraud",
        href: "/fraud/analyses",
        labelKey: "nav.analyses",
        permission: "fraud:read",
      },
    ]);
  });
});
