import { expect, type Page } from "@playwright/test";

/** Wait until the dynamically loaded workflow builder is interactive. */
export async function waitForBuilderReady(page: Page) {
  await expect(page.getByText("Loading builder…")).toHaveCount(0);
  await expect(page.getByPlaceholder("Workflow name…")).toBeVisible({
    timeout: 20_000,
  });
  await expect(page.getByText("Steps", { exact: true })).toBeVisible({
    timeout: 20_000,
  });
  await expect(
    page.getByRole("button", { name: /^What to extract/i })
  ).toBeVisible({ timeout: 20_000 });
}

/** Open the Test & deploy step in the workflow builder sidebar. */
export async function goToTestDeployStep(page: Page) {
  await waitForBuilderReady(page);

  const stepNav = page
    .locator("main aside")
    .filter({ has: page.getByText("Steps", { exact: true }) });
  const stepBtn = stepNav.getByRole("button", { name: /^Test & deploy/i });

  for (let attempt = 0; attempt < 3; attempt += 1) {
    await expect(stepBtn).toBeEnabled({ timeout: 20_000 });
    await stepBtn.scrollIntoViewIfNeeded();
    await stepBtn.click();
    try {
      await expect(page.getByRole("button", { name: "Extract + validate" })).toBeVisible({
        timeout: 5_000,
      });
      return;
    } catch {
      // Builder can still be hydrating; retry step navigation.
    }
  }

  await expect(page.getByRole("button", { name: "Extract + validate" })).toBeVisible({
    timeout: 20_000,
  });
}

/** Click the extract + validate CTA on the Test & deploy step. */
export async function clickExtractValidate(page: Page) {
  const runBtn = page.getByRole("button", { name: "Extract + validate" });
  await expect(runBtn).toBeVisible({ timeout: 20_000 });
  await runBtn.click();
}

/** Fill the workflow title and wait for a successful save PUT. */
export async function saveWorkflowName(page: Page, workflowId: string, name: string) {
  const nameInput = page.getByPlaceholder("Workflow name…");
  await nameInput.click({ clickCount: 3 });
  await nameInput.fill(name);
  await expect(nameInput).toHaveValue(name);

  const saveResponse = page.waitForResponse(
    (resp) =>
      resp.url().includes(`/api/workflows/${workflowId}`) &&
      resp.request().method() === "PUT"
  );
  await page.getByRole("button", { name: "Save draft" }).click();
  const response = await saveResponse;
  expect(response.ok()).toBeTruthy();
  const body = (await response.json()) as { workflow?: { name?: string } };
  expect(body.workflow?.name).toBe(name);
}
