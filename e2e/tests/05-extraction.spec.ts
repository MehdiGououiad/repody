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

  test("a sample is read in Test & deploy, values land in Fields, rules judge the sample", async ({
    page,
  }) => {
    const watch = watchErrors(page);
    await openBuilder(page, workflow.id);

    // Drop a sample in Fields; it carries over to Test & deploy.
    await page.locator('input[type="file"]').first().setInputFiles(SAMPLE_DOCUMENT);
    await expect(page.getByText("Facture.pdf")).toBeVisible();
    await expect(page.getByRole("tab", { name: /Invoice/ })).toBeVisible();

    await page
      .getByRole("toolbar", { name: "Steps" })
      .getByRole("button", { name: /Test & deploy/ })
      .click();
    await expect(page.getByText("Facture.pdf")).toBeVisible();
    const extract = page.getByRole("button", { name: /Extract and validate/ });
    await expect(extract).toBeEnabled();

    await extract.click();
    await expect(page.getByRole("button", { name: /Running/ }).first()).toBeVisible();
    const openReport = page.getByRole("link", { name: "Open report" }).first();
    await expect(openReport).toBeVisible({ timeout: 540_000 });

    // The report opens in a new tab.
    const tab = page.waitForEvent("popup");
    await openReport.click();
    const report = await tab;
    await expect(report).toHaveURL(/\/audits\/[^/]+$/);
    await expect(report.getByText("Facture.pdf").first()).toBeVisible();

    // The rules step shows how each rule did on the sample.
    await page
      .getByRole("toolbar", { name: "Steps" })
      .getByRole("button", { name: /Rules/ })
      .click();
    await expect(page.getByText(/(Holds|Fails) on the sample|Not evaluated/).first()).toBeVisible();

    // Back in Fields, extracted values appear next to the fields.
    await page
      .getByRole("toolbar", { name: "Steps" })
      .getByRole("button", { name: /Fields/ })
      .click();
    await expect(page.getByText(/\d+ of \d+ found/)).toBeVisible();
    const invoice = page.getByRole("region", { name: "Invoice" });
    const values = invoice.locator("li").filter({ hasNotText: "—" });
    await expect(values.first()).toBeVisible();

    watch.expectNoErrors();
  });
});
