import { test, expect } from "@playwright/test";
import {
  clickExtractValidate,
  goToTestDeployStep,
  saveWorkflowName,
  waitForBuilderReady,
} from "../helpers/workflow-builder";

const WORKFLOW_ID = "wf-invoice-audit";
const SEED_WORKFLOW_NAME = "Invoice Audit Pipeline";

test.describe("Workflow builder — test run", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`/workflows/${WORKFLOW_ID}/edit`);
    await waitForBuilderReady(page);
  });

  test("dry-run panel shows extraction preview", async ({ page }) => {
    // Step 0: documents — dry-run sidebar on xl; trigger manual run on smaller viewports
    await expect(page.getByText(/live test|dry run/i).first()).toBeVisible({ timeout: 20_000 });
  });

  test("full test run produces audit report link", async ({ page }) => {
    await goToTestDeployStep(page);
    await clickExtractValidate(page);

    await expect(page.getByText(/running/i).first()).toBeVisible({
      timeout: 10_000,
    }).catch(() => {});

    await expect(
      page.getByText(/passed|failed|warning|rule/i).first()
    ).toBeVisible({ timeout: 180_000 });

    const reportLink = page.getByRole("link", {
      name: /Open report|View full audit report/i,
    });
    await expect(reportLink.first()).toBeVisible();
  });

  test("save draft persists workflow name", async ({ page }) => {
    const uniqueName = `E2E Saved ${Date.now()}`;
    try {
      await saveWorkflowName(page, WORKFLOW_ID, uniqueName);
      await page.reload({ waitUntil: "networkidle" });
      await expect(page.getByPlaceholder("Workflow name…")).toHaveValue(uniqueName, {
        timeout: 20_000,
      });
    } finally {
      await saveWorkflowName(page, WORKFLOW_ID, SEED_WORKFLOW_NAME);
    }
  });
});
