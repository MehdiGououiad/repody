import path from "node:path";
import { expect, test } from "@playwright/test";
import { SAMPLE_DOCUMENT } from "../helpers/document";
import {
  clickExtractValidate,
  goToTestDeployStep,
  waitForBuilderReady,
} from "../helpers/workflow-builder";

test.describe("Document upload (sample fixture)", () => {
  test("upload sample document in test-run step", async ({ page }) => {
    const fileName = path.basename(SAMPLE_DOCUMENT);

    await page.goto("/workflows/wf-invoice-audit/edit");
    await waitForBuilderReady(page);

    await goToTestDeployStep(page);

    const fileInput = page.locator('input[type="file"]').first();
    await fileInput.setInputFiles(SAMPLE_DOCUMENT);

    await expect(page.getByText(fileName)).toBeVisible({ timeout: 10_000 });

    await clickExtractValidate(page);

    await expect(page.getByText(/passed|failed|warning|rule/i).first()).toBeVisible({
      timeout: 180_000,
    });
  });
});
