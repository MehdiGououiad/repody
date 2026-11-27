import { describe, expect, test } from "bun:test";
import { parseEnvModules, resolveActiveWorkspace } from "./manifests";

describe("manifests", () => {
  test("parseEnvModules filters unknown names and deduplicates", () => {
    expect(parseEnvModules("idp, fraud, INVALID, idp")).toEqual(["idp", "fraud"]);
    expect(parseEnvModules(undefined)).toEqual([]);
  });

  test("resolveActiveWorkspace picks workspace from route or entitlements", () => {
    const both = { status: "active" as const, modules: ["idp", "fraud"] as const };
    const fraudOnly = { status: "active" as const, modules: ["fraud"] as const };

    expect(resolveActiveWorkspace("/hub", both)).toBe("hub");
    expect(resolveActiveWorkspace("/fraud/frd-123", both)).toBe("fraud");
    expect(resolveActiveWorkspace("/cases/case-1", both)).toBe("cases");
    expect(resolveActiveWorkspace("/workflows", both)).toBe("idp");
    expect(resolveActiveWorkspace("/settings", fraudOnly)).toBe("fraud");
  });
});
