import { expect, test } from "@playwright/test";
import { fetchOidcEnabled, loginViaKeycloak } from "../helpers/auth";
import { KEYCLOAK_VIEWER, WEB_URL } from "../helpers/env";
import { openBuilder, watchErrors } from "../helpers/ui";

// What a viewer gets: what their role allows, shown as such, and never the Access denied page.
test("a viewer reads workflows and runs, and the app offers nothing they cannot do", async ({
  browser,
}) => {
  test.skip(!(await fetchOidcEnabled()), "OIDC disabled on this stack");
  const context = await browser.newContext({
    baseURL: WEB_URL,
    storageState: { cookies: [], origins: [] },
  });
  const page = await context.newPage();
  try {
    await loginViaKeycloak(page, "/dashboard", KEYCLOAK_VIEWER);
    const watch = watchErrors(page);

    // The Overview needs metrics: the viewer lands on Runs, and the nav leaves it out.
    await page.goto("/dashboard");
    await expect(page).toHaveURL(/\/audits$/);
    const nav = page.getByRole("navigation", { name: "Main" });
    await expect(nav.getByRole("link", { name: /^Overview/ })).toHaveCount(0);
    await expect(nav.getByRole("link", { name: /^Runs/ })).toBeVisible();
    await expect(page.getByRole("link", { name: "New workflow" })).toHaveCount(0);

    // Settings says what the role allows.
    await nav.getByRole("link", { name: /^Settings/ }).click();
    await expect(page.getByText("Your access")).toBeVisible();
    await expect(page.getByText("Viewer", { exact: true })).toBeVisible();
    await expect(page.getByText("Document model")).toHaveCount(0);

    // The builder opens read only: no save, fields disabled, deploying explained in step 3.
    await openBuilder(page, "wf-invoice-audit");
    await expect(page.getByText("View only")).toBeVisible();
    await expect(page.getByRole("button", { name: "Save draft" })).toHaveCount(0);
    await expect(page.getByRole("textbox", { name: "Workflow name" })).toHaveAttribute(
      "readonly",
      "",
    );
    await page
      .getByRole("toolbar", { name: "Steps" })
      .getByRole("button", { name: /Test & deploy/ })
      .click();
    const deploy = page.getByRole("button", { name: /Deploy|Redeploy/ }).first();
    await expect(deploy).toHaveAttribute("aria-disabled", "true");
    await deploy.hover();
    await expect(page.getByRole("tooltip")).toContainText("Your role does not allow this.");

    await expect(page).not.toHaveURL(/unauthorized/);
    watch.expectNoErrors();
  } finally {
    await context.close();
  }
});
