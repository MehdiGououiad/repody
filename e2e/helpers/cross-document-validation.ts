import path from "path";
import { expect, type Page } from "@playwright/test";
import { apiAuthHeaders, API } from "./api";
import {
  clickExtractValidate,
  goToTestDeployStep,
  waitForBuilderReady,
} from "./workflow-builder";

export const FACTURE_FIXTURE = path.join(
  process.cwd(),
  "e2e",
  "fixtures",
  "documents",
  "Facture.pdf"
);

export const COMMERCIAL_INVOICE_FIXTURE = path.join(
  process.cwd(),
  "e2e",
  "fixtures",
  "documents",
  "commercial-invoice.png"
);

type WorkflowPayload = {
  id: string;
  name: string;
  description: string;
  status: string;
  owner: string;
  documents: Array<{
    id: string;
    documentType: string;
    schema: Array<{ id: string; name: string; description: string; templateType?: string }>;
  }>;
  rules: unknown[];
};

export async function createCrossDocWorkflow(request: {
  post: (url: string, options?: object) => Promise<{ ok: () => boolean; json: () => Promise<unknown> }>;
  put: (url: string, options?: object) => Promise<{ ok: () => boolean }>;
}): Promise<{ workflowId: string; docAId: string; docBId: string }> {
  const ts = Date.now();
  const created = await request.post(`${API}/v1/workflows`, {
    headers: apiAuthHeaders({ "content-type": "application/json" }),
    data: {
      name: `E2E Cross-doc ${ts}`,
      description: "Inter-document validation UI test",
      owner: "E2E",
    },
  });
  expect(created.ok()).toBeTruthy();
  const body = (await created.json()) as { workflow: WorkflowPayload };
  const workflowId = body.workflow.id;
  const docAId = `doc-a-${ts}`;
  const docBId = `doc-b-${ts}`;

  const payload: WorkflowPayload = {
    ...body.workflow,
    name: `E2E Cross-doc ${ts}`,
    documents: [
      {
        id: docAId,
        documentType: "Facture 1",
        schema: [
          {
            id: `f-a-${ts}`,
            name: "total_amount",
            description: "Total TTC",
            templateType: "number",
          },
        ],
      },
      {
        id: docBId,
        documentType: "Facture 2",
        schema: [
          {
            id: `f-b-${ts}`,
            name: "total_amount",
            description: "Total TTC",
            templateType: "number",
          },
        ],
      },
    ],
    rules: [],
  };

  const saved = await request.put(`${API}/v1/workflows/${workflowId}`, {
    headers: apiAuthHeaders({ "content-type": "application/json" }),
    data: payload,
  });
  expect(saved.ok()).toBeTruthy();

  return { workflowId, docAId, docBId };
}

export async function goToRulesStep(page: Page) {
  await waitForBuilderReady(page);
  const stepNav = page
    .locator("main aside")
    .filter({ has: page.getByText("Steps", { exact: true }) });
  await stepNav.getByRole("button", { name: /^Validation rules/i }).click();
  await expect(page.getByRole("button", { name: "New logic rule" })).toBeVisible({
    timeout: 20_000,
  });
}

export async function addCrossDocumentTotalRule(page: Page, ruleName: string) {
  await page.getByRole("button", { name: "New logic rule" }).click();

  const ruleCard = page
    .locator(".panel-elevated")
    .filter({ has: page.getByPlaceholder("Rule name…") })
    .last();
  await ruleCard.getByPlaceholder("Rule name…").fill(ruleName);
  await ruleCard.getByRole("button", { name: "Cross-doc" }).click();

  await ruleCard.getByRole("combobox").first().click();
  await page.getByRole("option", { name: "Facture 1.total_amount" }).click();

  await ruleCard.getByRole("button", { name: "→ field" }).click();
  await ruleCard.getByRole("combobox").nth(2).click();
  await page.getByRole("option", { name: "Facture 2.total_amount" }).click();

  await expect(ruleCard.getByText(/facture_1__total_amount == facture_2__total_amount/i)).toBeVisible();
}

export async function uploadDocumentsForCrossTest(
  page: Page,
  files: { docLabel: string; filePath: string }[]
) {
  await goToTestDeployStep(page);

  for (const { docLabel, filePath } of files) {
    const card = page.locator(".panel-elevated").filter({ hasText: docLabel }).first();
    const input = card.locator('input[type="file"]');
    await input.setInputFiles(filePath);
    await expect(card.getByText(path.basename(filePath))).toBeVisible({ timeout: 10_000 });
  }
}

export async function runExtractValidateAndWait(page: Page) {
  await clickExtractValidate(page);
  await expect(
    page.getByText(/All checks passed|Validation failed|Passed with warnings/i).first()
  ).toBeVisible({ timeout: 300_000 });
  await expect(page.getByText("Rule-by-rule results")).toBeVisible({ timeout: 10_000 });
}

export async function expectRuleResult(page: Page, ruleName: string, detailPattern: RegExp) {
  const ruleRow = page.locator("div").filter({ hasText: ruleName }).filter({
    has: page.locator("text=/passed|failed|skipped|error/i"),
  }).first();
  await expect(ruleRow).toBeVisible();
  await expect(page.getByText(detailPattern).first()).toBeVisible();
}

export async function deleteWorkflow(request: {
  delete: (url: string, options?: object) => Promise<{ ok: () => boolean; status: () => number }>;
}, workflowId: string) {
  const res = await request.delete(`${API}/v1/workflows/${workflowId}`, {
    headers: apiAuthHeaders(),
  });
  expect([200, 403, 404]).toContain(res.status());
}
