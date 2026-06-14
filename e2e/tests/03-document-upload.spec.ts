import path from "path";
import { test, expect } from "@playwright/test";
import { hasSampleDocument, resolveSampleDocument } from "../helpers/document";
import { clickExtractValidate, goToTestDeployStep, waitForBuilderReady } from "../helpers/workflow-builder";

test.describe("Document upload (sample fixture)", () => {
  test.skip(!hasSampleDocument(), "Add a file to e2e/fixtures/documents/ (see README)");

  test("upload sample document in test-run step", async ({ page }) => {
    const samplePath = resolveSampleDocument()!;
    const fileName = path.basename(samplePath);

    await page.goto("/workflows/wf-invoice-audit/edit");
    await waitForBuilderReady(page);

    await goToTestDeployStep(page);

    const fileInput = page.locator('input[type="file"]').first();
    await fileInput.setInputFiles(samplePath);

    await expect(page.getByText(fileName)).toBeVisible({ timeout: 10_000 });

    await clickExtractValidate(page);

    await expect(
      page.getByText(/passed|failed|warning|rule/i).first()
    ).toBeVisible({ timeout: 180_000 });
  });
});
