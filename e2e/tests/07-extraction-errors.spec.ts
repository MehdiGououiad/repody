import path from "path";
import { test, expect } from "@playwright/test";
import { hasSampleDocument, resolveSampleDocument } from "../helpers/document";
import {
  clickExtractValidate,
  goToTestDeployStep,
  waitForBuilderReady,
} from "../helpers/workflow-builder";

const WORKFLOW_ID = "wf-invoice-audit";

test.describe("Extraction and validation errors", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`/workflows/${WORKFLOW_ID}/edit`);
    await waitForBuilderReady(page);
    await goToTestDeployStep(page);
  });

  test("inline test run surfaces failed rule validation", async ({ page }) => {
    await clickExtractValidate(page);

    await expect(
      page.getByText(/passed|failed|warning|rule/i).first()
    ).toBeVisible({ timeout: 180_000 });

    const failedRule = page.getByText(/Math integrity|failed|validation failed/i).first();
    await expect(failedRule).toBeVisible();
  });

  test.skip(!hasSampleDocument(), "Add a file to e2e/fixtures/documents/ (see README)");

  test("document upload run completes or surfaces extraction error", async ({ page }) => {
    const samplePath = resolveSampleDocument()!;
    const fileName = path.basename(samplePath);

    const fileInput = page.locator('input[type="file"]').first();
    await fileInput.setInputFiles(samplePath);
    await expect(page.getByText(fileName)).toBeVisible({ timeout: 10_000 });

    await clickExtractValidate(page);

    const outcome = page
      .getByRole("alert")
      .filter({ hasText: /Test run failed/i })
      .or(page.getByText(/passed|failed|warning|rule/i).first());

    await expect(outcome.first()).toBeVisible({ timeout: 180_000 });
  });
});
