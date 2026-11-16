import { expect, test } from "@playwright/test";
import { fetchOidcEnabled, loginViaKeycloak } from "../helpers/auth";
import { KEYCLOAK_ADMIN, WEB_URL } from "../helpers/env";
import { watchErrors } from "../helpers/ui";

// A platform admin sets up a client: its group, a user with a one-time password, credits; and
// the audit log keeps each step.
test("a platform admin creates a client, invites a user and gives it credits", async ({
  browser,
}) => {
  test.skip(!(await fetchOidcEnabled()), "OIDC disabled on this stack");
  const context = await browser.newContext({
    baseURL: WEB_URL,
    storageState: { cookies: [], origins: [] },
  });
  const page = await context.newPage();
  const slug = `e2e-${Date.now().toString(36)}`;
  const account = `client-${slug}`;
  try {
    await loginViaKeycloak(page, "/admin", KEYCLOAK_ADMIN);
    const watch = watchErrors(page);
    await page.goto("/admin");
    await expect(page.getByRole("heading", { name: "Admin" })).toBeVisible();

    await page.getByRole("button", { name: "New client" }).click();
    await page.getByRole("textbox", { name: "Name" }).fill(slug);
    await page.getByRole("button", { name: "Create", exact: true }).click();
    await expect(page.getByText(`${account} created`)).toBeVisible();

    await page.getByRole("link", { name: account }).click();
    await expect(page).toHaveURL(new RegExp(`/admin/clients/${account}$`));

    await page.getByRole("button", { name: "Invite user" }).click();
    await page.getByRole("textbox", { name: "Email" }).fill(`user@${slug}.test`);
    await page.getByRole("button", { name: "Invite", exact: true }).click();
    const password = page.getByRole("dialog", { name: /Temporary password/ });
    await expect(password).toBeVisible();
    await expect(password.locator("code")).toHaveText(/\S{12,}/);
    await password.getByRole("button", { name: "Done" }).click();
    await expect(page.getByRole("cell", { name: `user@${slug}.test` })).toBeVisible();

    await page.getByRole("button", { name: "Give credits" }).click();
    await page.getByRole("textbox", { name: "Note" }).fill("e2e trial");
    await page.getByRole("button", { name: "Give", exact: true }).click();
    await expect(page.getByText(`${account} now has 200 credits`)).toBeVisible();

    await expect(page.getByText("Credits granted")).toBeVisible();
    await expect(page.getByText("User invited")).toBeVisible();
    watch.expectNoErrors();
  } finally {
    await context.close();
  }
});
