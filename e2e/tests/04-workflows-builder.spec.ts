import { expect, type Page, test } from "@playwright/test";
import { API, apiAuthHeaders } from "../helpers/api";
import { loginViaKeycloak } from "../helpers/auth";
import { KEYCLOAK_ADMIN, WEB_URL } from "../helpers/env";
import {
  createWorkflow,
  dropWorkflow,
  open,
  openBuilder,
  type TempWorkflow,
  watchErrors,
} from "../helpers/ui";

async function fetchWorkflow(page: Page, id: string) {
  const response = await page.request.get(`${API}/v1/workflows/${id}`, {
    headers: apiAuthHeaders(),
  });
  return response.json();
}

test.describe("Workflows list", () => {
  test("X selects a row, the bar deletes it after a confirmation", async ({ browser, request }) => {
    const workflow = await createWorkflow(request, `QA delete ${Date.now()}`);
    // Deleting is admin-only: an admin's own session (the suite signs in as an operator).
    const context = await browser.newContext({
      baseURL: WEB_URL,
      storageState: { cookies: [], origins: [] },
    });
    const page = await context.newPage();
    await loginViaKeycloak(page, "/workflows", KEYCLOAK_ADMIN);
    const watch = watchErrors(page);
    await open(page, "/workflows");
    const row = page.getByRole("listitem").filter({ hasText: workflow.name });
    await row.getByRole("link").focus();
    await page.keyboard.press("x");
    await expect(row.getByRole("checkbox")).toBeChecked();
    await expect(page.getByText("1 selected")).toBeVisible();

    // Escape clears the selection; the checkbox selects again.
    await page.keyboard.press("Escape");
    await expect(page.getByText("1 selected")).toBeHidden();
    await row.getByRole("checkbox").check();

    await page.getByRole("button", { name: "Delete selected" }).click();
    const question = page.getByRole("alertdialog");
    await expect(question).toContainText("Delete 1 workflow?");
    await expect(question).toContainText(workflow.name);
    await question.getByRole("button", { name: "Delete" }).click();
    await expect(page.getByText("1 workflow deleted")).toBeVisible();
    await expect(row).toBeHidden();
    watch.expectNoErrors();
    await context.close();
  });

  test("C opens a new workflow with its name focused; Ctrl+S saves it", async ({ page }) => {
    const watch = watchErrors(page);
    await open(page, "/workflows");
    await page.keyboard.press("c");
    await expect(page).toHaveURL(/\/workflows\/new$/);
    const name = page.getByRole("textbox", { name: "Workflow name" });
    await expect(name).toBeFocused();
    const title = `QA new ${Date.now()}`;
    await name.fill(title);
    await page.keyboard.press("Control+s");
    await expect(page).toHaveURL(/\/workflows\/[^/]+\/edit$/);
    const id = page.url().split("/").at(-2) ?? "";
    expect((await fetchWorkflow(page, id)).name).toBe(title);
    await page.request.delete(`${API}/v1/workflows/${id}`, { headers: apiAuthHeaders() });
    watch.expectNoErrors();
  });
});

test.describe("Builder", () => {
  let workflow: TempWorkflow;
  test.beforeEach(async ({ request }) => {
    workflow = await createWorkflow(request);
  });
  test.afterEach(async ({ request }) => {
    await dropWorkflow(request, workflow.id);
  });

  test("fields: add, name, type, list, duplicate error, remove; saved on Ctrl+S", async ({
    page,
  }) => {
    const watch = watchErrors(page);
    await openBuilder(page, workflow.id);
    const fields = page.getByRole("region", { name: "Invoice" }).getByRole("listitem");
    const before = await fields.count();

    await page.getByRole("button", { name: "Add field" }).click();
    await expect(fields).toHaveCount(before + 1);
    const added = fields.last();
    await expect(added.getByRole("textbox", { name: "Name" })).toBeFocused();
    await added.getByRole("textbox", { name: "Name" }).fill("due_date");
    await added.getByRole("textbox", { name: "What to extract" }).fill("Payment due date");
    await added.getByRole("combobox", { name: "Output format" }).click();
    await page
      .getByRole("option", { name: /^Date\b/ })
      .first()
      .click();
    await expect(added.getByRole("combobox", { name: "Output format" })).toContainText("Date");
    await added.getByRole("button", { name: "List" }).click();
    await expect(added.getByRole("button", { name: "List" })).toHaveAttribute(
      "aria-pressed",
      "true"
    );

    // A second field with the same name is refused.
    await page.getByRole("button", { name: "Add field" }).click();
    await fields.last().getByRole("textbox", { name: "Name" }).fill("due_date");
    await expect(page.getByText("Name must be unique").first()).toBeVisible();
    await fields.last().getByRole("button", { name: "Remove due_date" }).click();
    await expect(fields).toHaveCount(before + 1);

    await page.keyboard.press("Control+s");
    await expect
      .poll(async () =>
        (await fetchWorkflow(page, workflow.id)).documents[0].schema.find(
          (f: { name: string }) => f.name === "due_date"
        )
      )
      .toMatchObject({ description: "Payment due date", templateType: "date-list" });
    watch.expectNoErrors();
  });

  test("documents: add, rename, remove after a confirmation", async ({ page }) => {
    const watch = watchErrors(page);
    await openBuilder(page, workflow.id);
    const tabs = page.getByRole("tablist", { name: "Documents" }).getByRole("tab");
    await expect(tabs).toHaveCount(2);
    await page.getByRole("button", { name: "Add a document" }).click();
    await expect(tabs).toHaveCount(3);
    await expect(tabs.last()).toHaveAttribute("aria-selected", "true");
    const docName = page.getByRole("textbox", { name: "Document name" });
    await docName.fill("Delivery note");
    await expect(tabs.last()).toContainText("Delivery note");

    await page.getByRole("button", { name: "Document actions" }).click();
    await page.getByRole("menuitem", { name: "Remove document" }).click();
    const question = page.getByRole("alertdialog");
    await expect(question).toContainText("Delivery note");
    await question.getByRole("button", { name: "Remove" }).click();
    await expect(tabs).toHaveCount(2);
    watch.expectNoErrors();
  });

  test("import a template appends its fields", async ({ page }) => {
    const watch = watchErrors(page);
    await openBuilder(page, workflow.id);
    const fields = page.getByRole("region", { name: "Invoice" }).getByRole("listitem");
    const before = await fields.count();
    await page.getByRole("button", { name: "Import template" }).click();
    const dialog = page.getByRole("dialog", { name: "Import a JSON template" });
    const template = dialog.getByRole("textbox");
    await template.fill("{ not json");
    await dialog.getByRole("button", { name: "Append fields" }).click();
    await expect(dialog.getByText(/Invalid JSON/)).toBeVisible();
    await template.fill('{ "iban": "iban", "lines": [{ "label": "string", "amount": "number" }] }');
    await dialog.getByRole("button", { name: "Append fields" }).click();
    await expect(dialog).toBeHidden();
    await expect(fields).not.toHaveCount(before);
    const names = await page
      .getByRole("textbox", { name: "Name" })
      .evaluateAll((inputs) => inputs.map((input) => (input as HTMLInputElement).value));
    expect(names).toEqual(expect.arrayContaining(["iban", "lines", "label", "amount"]));
    watch.expectNoErrors();
  });

  test("rules: add, name, documents, severity, remove", async ({ page }) => {
    const watch = watchErrors(page);
    await openBuilder(page, workflow.id);
    await page.getByRole("tab", { name: /Rules/ }).click();
    const names = page.getByRole("textbox", { name: "Rule name…" });
    await expect(names).toHaveCount(1);
    await page.getByRole("button", { name: "Add a rule" }).click();
    await expect(names).toHaveCount(2);
    await names.last().fill("QA rule");

    const rule = page.locator("article, section, li").filter({ has: names.last() }).last();
    await rule.getByRole("combobox", { name: "If it fails" }).click();
    await page.getByRole("option", { name: "Flag for review" }).click();
    await expect(rule.getByRole("combobox", { name: "If it fails" })).toContainText(
      "Flag for review"
    );

    // Half written, the rule cannot be saved: the header says so, with the reason.
    await page.keyboard.press("Control+s");
    await expect(page.getByText("Not saved")).toBeVisible();
    await expect(page.getByText(/Choose a field on the left/).first()).toBeVisible();

    await rule.getByRole("combobox", { name: "Pick field" }).first().click();
    await page
      .getByRole("option", { name: /total_amount/ })
      .first()
      .click();
    await rule.getByPlaceholder("0").fill("0");
    await page.keyboard.press("Control+s");
    await expect(page.getByText("Saved", { exact: true })).toBeVisible();
    await page.keyboard.press("Control+s");
    await expect
      .poll(async () =>
        (await fetchWorkflow(page, workflow.id)).rules.find(
          (r: { name: string }) => r.name === "QA rule"
        )
      )
      .toMatchObject({ severity: "flag" });

    await rule.getByRole("button", { name: "Rule actions" }).click();
    await page.getByRole("menuitem", { name: "Remove rule" }).click();
    await page.getByRole("alertdialog").getByRole("button", { name: "Remove" }).click();
    await expect(names).toHaveCount(1);
    watch.expectNoErrors();
  });

  test("publish shows the API with a key", async ({ page }) => {
    const watch = watchErrors(page);
    await openBuilder(page, workflow.id);
    await page.getByRole("tab", { name: /Publish/ }).click();
    await page.getByRole("tabpanel").getByRole("button", { name: "Publish" }).click();
    await expect(page.getByText("Live").first()).toBeVisible();
    await expect(page.getByText(/wbk_/).first()).toBeVisible();
    const saved = await fetchWorkflow(page, workflow.id);
    expect(saved.status).toBe("active");
    watch.expectNoErrors();
  });
});
