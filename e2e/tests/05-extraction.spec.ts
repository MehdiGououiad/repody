import { expect, test } from "@playwright/test";
import { SAMPLE_DOCUMENT } from "../helpers/document";
import {
  createWorkflow,
  dropWorkflow,
  openBuilder,
  type TempWorkflow,
  watchErrors,
} from "../helpers/ui";

/**
 * A real extraction through the model: slow (a cold model takes minutes) and it uses GPU time,
 * so it runs once, on the sample invoice.
 */
test.describe("Extraction", () => {
  test.setTimeout(600_000);
  let workflow: TempWorkflow;
  test.beforeAll(async ({ request }) => {
    workflow = await createWorkflow(request);
  });
  test.afterAll(async ({ request }) => {
    await dropWorkflow(request, workflow.id);
  });

  test("a sample is read, values land in the fields, rules judge the sample", async ({ page }) => {
    const watch = watchErrors(page);
    await openBuilder(page, workflow.id);
    const extract = page.getByRole("button", { name: /^Extract/ });
    await expect(extract).toBeDisabled();

    await page.locator('input[type="file"]').first().setInputFiles(SAMPLE_DOCUMENT);
    await expect(page.getByText("Facture.pdf")).toBeVisible();
    await expect(extract).toBeEnabled();
    await expect(page.getByRole("tab", { name: /Invoice/ })).toBeVisible();

    await page.keyboard.press("Control+Enter");
    await expect(page.getByRole("button", { name: /Extracting/ })).toBeVisible();
    await expect(page.getByText(/\d+ of \d+ found/)).toBeVisible({ timeout: 540_000 });

    // At least one field shows the value read from the invoice.
    const invoice = page.getByRole("region", { name: "Invoice" });
    const values = invoice.locator("li").filter({ hasNotText: "—" });
    await expect(values.first()).toBeVisible();

    // The rules step says how each rule did on the sample.
    await page.getByRole("tab", { name: /Rules/ }).click();
    await expect(page.getByText(/(Holds|Fails) on the sample|Not evaluated/).first()).toBeVisible();

    // Publish shows the last extraction; its report opens in a new tab (the sample stays here).
    await page.getByRole("tab", { name: /Publish/ }).click();
    await expect(page.getByRole("heading", { name: "Last extraction" })).toBeVisible();
    const tab = page.waitForEvent("popup");
    await page.getByRole("link", { name: "Open report" }).first().click();
    const report = await tab;
    await expect(report).toHaveURL(/\/audits\/[^/]+$/);
    await expect(report.getByText("Facture.pdf").first()).toBeVisible();
    watch.expectNoErrors();
  });
});
