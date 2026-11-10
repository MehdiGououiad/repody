import { describe, expect, it } from "vitest";
import { initials } from "@/lib/auth/account";
import { rolesFromAccessToken } from "@/lib/auth/jwt-claims";

const token = (claims: object) =>
  `e30.${Buffer.from(JSON.stringify(claims)).toString("base64url")}.sig`;

describe("roles", () => {
  it("come from realm roles and groups, as the API reads them", () => {
    const claims = { realm_access: { roles: ["viewer", "offline_access"] }, groups: ["/operator"] };
    expect(rolesFromAccessToken(token(claims))).toEqual(["operator", "viewer"]);
    expect(rolesFromAccessToken("not-a-jwt")).toEqual([]);
  });
});

describe("initials", () => {
  it("use the name, else the email", () => {
    expect(initials({ name: "Ada Lovelace", email: null, roles: [] })).toBe("AL");
    expect(initials({ name: null, email: "grace@example.com", roles: [] })).toBe("GR");
  });
});
