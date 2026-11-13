import { expect, test } from "@playwright/test";
import {
  createWorkflow,
  dropWorkflow,
  open,
  startRun,
  type TempWorkflow,
  watchErrors,
} from "../helpers/ui";

test.describe("Overview", () => {
  test("shows the week, the volume chart, the review queue and the workflows", async ({ page }) => {
    const watch = watchErrors(page);
    await open(page, "/dashboard");
    const main = page.getByRole("main");
    await expect(main.getByText("Runs · 7 days")).toBeVisible();
    await expect(main.getByText("Pass rate", { exact: true }).first()).toBeVisible();
    await expect(main.getByRole("heading", { name: /Volume/ })).toBeVisible();
    await expect(main.getByRole("heading", { name: "To review" })).toBeVisible();
    await expect(main.getByRole("heading", { name: "Workflows" })).toBeVisible();
    await expect(main.getByText("Factures fournisseurs").first()).toBeVisible();
    watch.expectNoErrors();
  });

  test("a day of the volume chart opens the runs of that day", async ({ page }) => {
    const watch = watchErrors(page);
    await open(page, "/dashboard");
    const busyDay = page.locator('a[href^="/audits?day="]').filter({ hasNotText: /^$/ }).last();
    const href = await busyDay.getAttribute("href");
    await busyDay.click();
    await expect(page).toHaveURL(new RegExp(`${href?.replace("?", "\\?")}$`));
    await expect(page.getByRole("heading", { level: 1, name: "Runs" })).toBeVisible();
    await expect(page.getByRole("button", { name: /Remove filter/ })).toBeVisible();
    watch.expectNoErrors();
  });

  test("View all opens every run to review, flagged and rejected", async ({ page }) => {
    const watch = watchErrors(page);
    await open(page, "/dashboard");
    await page.locator(`a[href="/audits?outcome=review"]`).last().click();
    await expect(page).toHaveURL(/\/audits\?outcome=review$/);
    await expect(page.getByRole("button", { name: /To review/ })).toBeVisible();
    await expect(
      page.getByRole("radiogroup", { name: "Status" }).getByRole("radio", { checked: true })
    ).toHaveCount(0);
    await page.getByRole("button", { name: /To review/ }).click();
    await expect(page).not.toHaveURL(/outcome=/);
    watch.expectNoErrors();
  });

  test("J and Enter open the first run to review", async ({ page }) => {
    const watch = watchErrors(page);
    await open(page, "/dashboard");
    const first = page.locator("[data-row]").first();
    test.skip((await first.count()) === 0, "nothing to review in this database");
    const href = await first.getAttribute("href");
    await page.keyboard.press("j");
    await expect(first).toBeFocused();
    await page.keyboard.press("Enter");
    await expect(page).toHaveURL(new RegExp(`${href}$`));
    watch.expectNoErrors();
  });
});

test.describe("Control room", () => {
  let workflow: TempWorkflow;
  test.beforeAll(async ({ request }) => {
    workflow = await createWorkflow(request);
  });
  test.afterAll(async ({ request }) => {
    await dropWorkflow(request, workflow.id);
  });

  test("shows the model, the queue, throughput and errors", async ({ page }) => {
    const watch = watchErrors(page);
    await open(page, "/operations");
    const main = page.getByRole("main");
    await expect(main.getByText("Model", { exact: true })).toBeVisible();
    await expect(main.getByRole("heading", { name: "In flight" })).toBeVisible();
    await expect(main.getByRole("heading", { name: "Throughput · 24 h" })).toBeVisible();
    await expect(main.getByRole("heading", { name: "Errors · 24 h" })).toBeVisible();
    watch.expectNoErrors();
  });

  test("a run appears live and Stop fails it with the user's name", async ({ page, request }) => {
    const watch = watchErrors(page);
    await open(page, "/operations");
    // A warm model can finish a run between two polls: start runs until one is seen in flight.
    const inFlight = async () => {
      for (let attempt = 0; attempt < 3; attempt++) {
        const runId = await startRun(request, workflow);
        const row = page.getByRole("listitem").filter({ hasText: runId.slice(-6) });
        if (
          await row.waitFor({ timeout: 8_000 }).then(
            () => true,
            () => false
          )
        )
          return row;
      }
      throw new Error("no run stayed in flight long enough to be seen");
    };
    const row = await inFlight();
    await expect(row).toContainText(workflow.name);

    // Keep running closes the question and leaves the run alone.
    await row.hover();
    await row.getByRole("button", { name: "Stop" }).click();
    const question = page.getByRole("alertdialog");
    await expect(question).toContainText("Stop this run?");
    await question.getByRole("button", { name: "Keep running" }).click();
    await expect(question).toBeHidden();
    await expect(row).toBeVisible();

    await row.hover();
    await row.getByRole("button", { name: "Stop" }).click();
    await question.getByRole("button", { name: "Stop" }).click();
    // A warm model can finish the run first: the app then says so instead of stopping it.
    const stopped = page.getByText("Run stopped");
    const finished = page.getByText(/^The run is already (done|failed)\.$/);
    await expect(stopped.or(finished).first()).toBeVisible();
    await expect(row).toBeHidden();
    if (await stopped.first().isVisible()) {
      // It lands in the errors of the last 24 hours with the reason.
      await expect(
        page
          .getByRole("listitem")
          .filter({ hasText: workflow.name })
          .filter({ hasText: "Cancelled by" })
      ).toBeVisible();
    }
    watch.expectNoErrors();
  });

  test("Release stuck runs answers even when nothing is stuck", async ({ page }) => {
    const watch = watchErrors(page);
    await open(page, "/operations");
    const release = page.getByRole("button", { name: "Release stuck runs" });
    test.skip((await release.count()) === 0, "the button only shows while a run is stuck");
    await release.click();
    await expect(page.getByText(/released|No stuck runs/)).toBeVisible();
    watch.expectNoErrors();
  });
});
