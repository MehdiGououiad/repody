import { test, expect } from "@playwright/test";
import {
  addCrossDocumentTotalRule,
  COMMERCIAL_INVOICE_FIXTURE,
  createCrossDocWorkflow,
  deleteWorkflow,
  FACTURE_FIXTURE,
  goToRulesStep,
  runExtractValidateAndWait,
  uploadDocumentsForCrossTest,
} from "../helpers/cross-document-validation";

test.describe("Cross-document validation — UI", () => {
  test("matching totals pass when configured via condition builder", async ({ page, request }) => {
    const { workflowId } = await createCrossDocWorkflow(request);

    try {
      await page.goto(`/workflows/${workflowId}/edit`);
      await goToRulesStep(page);
      await addCrossDocumentTotalRule(page, "Totals must match");

      await uploadDocumentsForCrossTest(page, [
        { docLabel: "Facture 1", filePath: FACTURE_FIXTURE },
        { docLabel: "Facture 2", filePath: FACTURE_FIXTURE },
      ]);

      await runExtractValidateAndWait(page);

      await expect(page.getByText("Totals must match").first()).toBeVisible();
      await expect(page.getByText("All checks passed")).toBeVisible();
      await expect(page.getByText(/All conditions satisfied/i).first()).toBeVisible();
    } finally {
      await deleteWorkflow(request, workflowId);
    }
  });

  test("mismatched totals fail cross-document rule in UI results", async ({ page, request }) => {
    test.setTimeout(600_000);
    const { workflowId } = await createCrossDocWorkflow(request);

    try {
      await page.goto(`/workflows/${workflowId}/edit`);
      await goToRulesStep(page);
      await addCrossDocumentTotalRule(page, "Totals must match");

      await uploadDocumentsForCrossTest(page, [
        { docLabel: "Facture 1", filePath: FACTURE_FIXTURE },
        { docLabel: "Facture 2", filePath: COMMERCIAL_INVOICE_FIXTURE },
      ]);

      await runExtractValidateAndWait(page);

      await expect(page.getByText("Totals must match").first()).toBeVisible();
      await expect(page.getByText(/Validation failed|evaluated to false/i).first()).toBeVisible();
    } finally {
      await deleteWorkflow(request, workflowId);
    }
  });
});
