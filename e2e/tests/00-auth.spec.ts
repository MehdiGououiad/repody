import { test, expect } from "@playwright/test";
import { fetchOidcEnabled } from "../helpers/auth";
import { API, apiAuthHeaders } from "../helpers/api";

import { WEB_URL } from "../helpers/env";

test.describe("Authentication", () => {
  test("unauthenticated API calls are rejected when OIDC is enabled", async ({ browser }) => {
    test.skip(!(await fetchOidcEnabled()), "OIDC disabled on this stack");

    const context = await browser.newContext({
      baseURL: WEB_URL,
      storageState: { cookies: [], origins: [] },
    });
    const page = await context.newPage();
    try {
      await page.goto("/login");
      const status = await page.evaluate(async () => {
        const response = await fetch("/api/v1/workflows");
        return response.status;
      });
      expect(status).toBe(401);
    } finally {
      await context.close();
    }
  });

  test("unauthenticated users are redirected from dashboard to login", async ({ browser }) => {
    test.skip(!(await fetchOidcEnabled()), "OIDC disabled on this stack");

    const context = await browser.newContext({
      baseURL: WEB_URL,
      storageState: { cookies: [], origins: [] },
    });
    const page = await context.newPage();
    try {
      await page.goto("/dashboard");
      await expect(page).toHaveURL(/\/login/);
      await expect(page.getByRole("button", { name: /Continue with Keycloak/i })).toBeVisible();
    } finally {
      await context.close();
    }
  });

  test("authenticated session reaches dashboard", async ({ page }) => {
    test.skip(!(await fetchOidcEnabled()), "OIDC disabled on this stack");

    await page.goto("/dashboard");
    await expect(page).toHaveURL(/\/dashboard/);
    await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();
  });

  test("API rejects workflow runs without credentials when OIDC is enabled", async ({
    request,
  }) => {
    test.skip(!(await fetchOidcEnabled()), "OIDC disabled on this stack");

    const res = await request.post(`${API}/v1/workflows/wf-invoice-audit/runs/json`, {
      data: { snapshot: { documents: [], rules: [], workflowName: "E2E" } },
    });
    expect(res.status()).toBe(401);
  });

  test("API accepts authenticated workflow list when OIDC is enabled", async ({ request }) => {
    test.skip(!(await fetchOidcEnabled()), "OIDC disabled on this stack");

    const res = await request.get(`${API}/v1/workflows`, {
      headers: apiAuthHeaders(),
    });
    expect(res.ok()).toBeTruthy();
    const body = (await res.json()) as { workflows: unknown[] };
    expect(Array.isArray(body.workflows)).toBeTruthy();
  });
});
