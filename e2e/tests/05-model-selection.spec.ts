import { expect, test } from "@playwright/test";

const API = process.env.E2E_API_URL ?? "http://localhost:8000";

test("users can select Repody VLM for document extraction", async ({
  page,
  request,
}) => {
  await page.goto("/workflows/new");
  await expect(page.getByLabel("Read path")).toBeEnabled();
  await page.getByPlaceholder("Workflow name…").fill(`Model selection ${Date.now()}`);
  await page.getByLabel("Document name").fill("Invoice");
  await page.getByRole("button", { name: "Add field" }).click();
  await page.getByPlaceholder("e.g. invoice_number").fill("total_amount");
  await page
    .getByPlaceholder(/unique invoice identifier/i)
    .fill("Total TTC including tax");

  await page.getByLabel("Read path").click();
  await page.getByRole("option", { name: "Document model" }).click();

  await page.locator('[id^="extraction-model-"]').click();
  await page.getByRole("option", { name: /Repody VLM/ }).click();
  await expect(
    page.getByText("Direct structured extraction", { exact: true })
  ).toBeVisible();
  await expect(page.getByText("Repody VLM")).toBeVisible();

  await page.getByRole("button", { name: "Save draft" }).click();
  await expect(page).toHaveURL(/\/workflows\/[^/]+\/edit/);
  const workflowId = page.url().match(/\/workflows\/([^/]+)\/edit/)?.[1];
  expect(workflowId).toBeTruthy();

  try {
    const response = await request.get(`${API}/v1/workflows/${workflowId}`);
    expect(response.ok()).toBeTruthy();
    const workflow = (await response.json()).workflow;
    expect(workflow.documents[0].extractionMode).toBe("document_model");
    expect(workflow.documents[0].ocrModel).toBe("repody:vlm");
    expect(workflow.documents[0].validationMode).toBe("logic_only");
    expect(workflow.documents[0].defaultLlmModel).toBeFalsy();
  } finally {
    if (workflowId) {
      await request.delete(`${API}/v1/workflows/${workflowId}`);
    }
  }
});
