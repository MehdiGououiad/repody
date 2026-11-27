import { describe, expect, test } from "bun:test";
import {
  type EntitlementState,
  hasModule,
  isOperational,
  type ModuleRouteTarget,
  resolveHomeRoute,
  showModuleSwitcher,
} from "./entitlements";

const MANIFESTS: readonly ModuleRouteTarget[] = [
  { id: "idp", basePath: "/idp" },
  { id: "fraud", basePath: "/fraud" },
  { id: "operator", basePath: "/operator" },
];

describe("entitlements", () => {
  test("single-module license bypasses hub directly into the owned workspace", () => {
    const fraudOnly: EntitlementState = { status: "active", modules: ["fraud"] };
    expect(isOperational(fraudOnly)).toBe(true);
    expect(hasModule(fraudOnly, "fraud")).toBe(true);
    expect(hasModule(fraudOnly, "idp")).toBe(false);
    expect(showModuleSwitcher(fraudOnly)).toBe(false);
    expect(resolveHomeRoute(fraudOnly, MANIFESTS)).toBe("/fraud");

    const idpOnly: EntitlementState = { status: "grace", modules: ["idp"], warning: "Grace" };
    expect(isOperational(idpOnly)).toBe(true);
    expect(resolveHomeRoute(idpOnly, MANIFESTS)).toBe("/idp");
  });

  test("multi-module license opens hub and enables switcher", () => {
    const duo: EntitlementState = { status: "active", modules: ["idp", "fraud"] };
    expect(showModuleSwitcher(duo)).toBe(true);
    expect(resolveHomeRoute(duo, MANIFESTS)).toBe("/hub");
  });

  test("expired or invalid license blocks all modules", () => {
    const expired: EntitlementState = { status: "expired", modules: ["idp", "fraud"] };
    expect(isOperational(expired)).toBe(false);
    expect(hasModule(expired, "idp")).toBe(false);
    expect(showModuleSwitcher(expired)).toBe(false);
    expect(resolveHomeRoute(expired, MANIFESTS)).toBe("/settings");
  });
});
