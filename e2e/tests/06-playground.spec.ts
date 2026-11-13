import { type Browser, expect, type Page, test } from "@playwright/test";
import { SAMPLE_DOCUMENT } from "../helpers/document";
import { watchErrors } from "../helpers/ui";

/**
 * The public playground (a deployment in demo mode, no sign-in). Runs only when
 * E2E_PLAYGROUND_URL is set, e.g. `E2E_PLAYGROUND_URL=http://localhost:3101`.
 */
const PLAYGROUND = process.env.E2E_PLAYGROUND_URL;
test.skip(!PLAYGROUND, "set E2E_PLAYGROUND_URL to a demo-mode deployment");
test.use({ baseURL: PLAYGROUND, storageState: { cookies: [], origins: [] } });

/** A visitor of their own: a fresh browser context, so a new visitor cookie. */
async function visitor(browser: Browser): Promise<Page> {
  const context = await browser.newContext({ baseURL: PLAYGROUND, locale: "en-US" });
  return context.newPage();
}

async function openExample(page: Page, name: string) {
  await page.goto("/workflows");
  await page
    .getByRole("link", { name: new RegExp(name) })
    .first()
    .click();
  await expect(page.getByRole("tab", { name: /Extraction/ })).toBeVisible({ timeout: 60_000 });
}

test("a visitor edits an example and keeps their own copy, which nobody else sees", async ({
  browser,
}) => {
  const alice = await visitor(browser);
  const watch = watchErrors(alice);
  await openExample(alice, "Factures fournisseurs");
  await expect(alice.getByText("Shared example")).toBeVisible();

  await alice.getByRole("button", { name: "Add field" }).click();
  await alice.getByRole("textbox", { name: "Name" }).last().fill("iban");
  await alice.keyboard.press("Control+s");
  await expect(alice.getByText("Your copy is saved")).toBeVisible();
  await expect(alice).toHaveURL(/\/workflows\/wf-[^/]+\/edit$/);
  await expect(alice.getByRole("textbox", { name: "Workflow name" })).toHaveValue(/my copy/);
  await expect(alice.getByRole("textbox", { name: "Name" }).last()).toHaveValue("iban");
  const copy = alice.url();

  const bob = await visitor(browser);
  await bob.goto("/workflows");
  await expect(bob.getByRole("link", { name: /my copy/ })).toHaveCount(0);
  const response = await bob.goto(copy);
  expect(response?.status()).toBe(404);
  watch.expectNoErrors();
});

test("extracting and publishing ask the visitor to contact us for credits", async ({ browser }) => {
  const alice = await visitor(browser);
  await openExample(alice, "Factures fournisseurs");
  const credits = alice.getByRole("dialog", { name: "Ready to extract?" });

  await alice.locator('input[type="file"]').first().setInputFiles(SAMPLE_DOCUMENT);
  await alice.keyboard.press("Control+Enter");
  await expect(credits).toBeVisible();
  await expect(credits.getByRole("link", { name: /Contact form/ })).toHaveAttribute(
    "href",
    /contact/
  );
  await credits.getByRole("button", { name: "Keep exploring" }).click();
  await expect(credits).toBeHidden();

  await alice
    .getByRole("button", { name: /^Publish/ })
    .first()
    .click();
  await expect(credits).toBeVisible();
  await credits.getByRole("button", { name: "Keep exploring" }).click();

  await alice.getByRole("button", { name: "Get credits" }).click();
  await expect(credits).toBeVisible();
});

test("the playground has no sign-in and shows the examples' reports", async ({ browser }) => {
  const alice = await visitor(browser);
  const watch = watchErrors(alice);
  const login = await alice.goto("/login");
  expect(new URL(login?.url() ?? "").pathname).toBe("/dashboard");
  await expect(alice.getByText("Playground").first()).toBeVisible();
  await alice.goto("/audits");
  await alice.locator("[data-row]").first().click();
  await expect(alice).toHaveURL(/\/audits\/run-/);
  await expect(alice.getByRole("img", { name: /Page 1/ }).first()).toBeVisible();
  watch.expectNoErrors();
});
