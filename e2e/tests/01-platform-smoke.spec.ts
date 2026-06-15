import { test, expect } from "@playwright/test";
import { API, apiGet } from "../helpers/api";

test.describe("Platform smoke", () => {
  test("API health", async () => {
    const res = await fetch(`${API}/v1/healthz`);
    expect(res.ok).toBeTruthy();
    const body = await res.json();
    expect(body.status).toBe("ok");
  });

  test("dashboard loads with KPIs and recent audits", async ({ page }) => {
    await page.goto("/dashboard");
    await expect(page.getByRole("heading", { name: /Control center/i })).toBeVisible();
    await expect(page.locator("main")).toBeVisible();
    // Seeded workflow banner or KPI cards
    await expect(page.getByText(/audit|pass rate|workflow/i).first()).toBeVisible();
  });

  test("workflows list includes seeded invoice workflow", async ({ page }) => {
    const { workflows } = await apiGet<{ workflows: { id: string; name: string }[] }>(
      "/workflows"
    );
    const invoice = workflows.find((w) => w.id === "wf-invoice-audit");
    expect(invoice).toBeTruthy();

    await page.goto("/workflows");
    await expect(page.getByText(invoice!.name)).toBeVisible();
  });

  test("audits list and seeded audit report", async ({ page }) => {
    await page.goto("/audits");
    await expect(page.getByText("AUD-2023-8902")).toBeVisible();

    await page.getByRole("link", { name: /AUD-2023-8902/i }).click();
    await expect(page).toHaveURL(/\/audits\/AUD-2023-8902/);
    await expect(page.getByText(/math integrity|subtotal|rule/i).first()).toBeVisible();
  });
});
