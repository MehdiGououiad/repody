import { expect, test } from "@playwright/test";
import { open, watchErrors } from "../helpers/ui";

const PAGES = [
  { path: "/dashboard", heading: "Overview" },
  { path: "/operations", heading: "Control room" },
  { path: "/workflows", heading: "Workflows" },
  { path: "/audits", heading: "Runs" },
  { path: "/settings", heading: "Settings" },
];

test.describe("Navigation and shell", () => {
  test("every page loads without an error, from the sidebar", async ({ page }) => {
    const watch = watchErrors(page);
    await open(page, "/dashboard");
    const nav = page.getByRole("navigation", { name: "Main" });
    for (const { path, heading } of PAGES) {
      await nav.getByRole("link", { name: new RegExp(`^${heading}`) }).click();
      await expect(page).toHaveURL(new RegExp(`${path}$`));
      await expect(page.getByRole("heading", { level: 1, name: heading })).toBeVisible();
      await expect(nav.getByRole("link", { name: new RegExp(`^${heading}`) })).toHaveAttribute(
        "aria-current",
        "page",
      );
    }
    watch.expectNoErrors();
  });

  test("G then a letter goes to each page, C creates a workflow", async ({ page }) => {
    const watch = watchErrors(page);
    await open(page, "/dashboard");
    await expect(page.getByRole("heading", { level: 1, name: "Overview" })).toBeVisible();
    for (const [key, path] of [
      ["c", "/operations"],
      ["w", "/workflows"],
      ["r", "/audits"],
      ["s", "/settings"],
      ["o", "/dashboard"],
    ]) {
      await page.keyboard.press("g");
      await page.keyboard.press(key);
      await expect(page).toHaveURL(new RegExp(`${path}$`));
    }
    await page.keyboard.press("c");
    await expect(page).toHaveURL(/\/workflows\/new$/);
    watch.expectNoErrors();
  });

  test("the command palette searches, navigates and switches the theme", async ({ page }) => {
    const watch = watchErrors(page);
    await open(page, "/dashboard");
    await page.keyboard.press("Control+k");
    const palette = page.getByRole("dialog");
    await expect(palette).toBeVisible();
    await palette.getByRole("combobox").fill("Settings");
    await page.keyboard.press("Enter");
    await expect(page).toHaveURL(/\/settings$/);
    await expect(palette).toBeHidden();

    await page.keyboard.press("/");
    await palette.getByRole("combobox").fill("Dark");
    await page.keyboard.press("Enter");
    await expect(page.locator("html")).toHaveClass(/dark/);
    await page.keyboard.press("Control+k");
    await palette.getByRole("combobox").fill("Light");
    await page.keyboard.press("Enter");
    await expect(page.locator("html")).not.toHaveClass(/dark/);

    await page.keyboard.press("Control+k");
    await palette.getByRole("combobox").fill("zzzz-nothing");
    await expect(palette.getByRole("status")).toHaveText("No results found.");
    await expect(palette.getByRole("option")).toHaveCount(0);
    // Escape clears the search first, then closes.
    await page.keyboard.press("Escape");
    await expect(palette.getByRole("combobox")).toHaveValue("");
    await page.keyboard.press("Escape");
    await expect(palette).toBeHidden();
    watch.expectNoErrors();
  });

  test("? lists the shortcuts of the page, [ hides and shows the sidebar", async ({ page }) => {
    const watch = watchErrors(page);
    await open(page, "/audits");
    await expect(page.getByRole("heading", { level: 1, name: "Runs" })).toBeVisible();
    await page.keyboard.press("Shift+?");
    const help = page.getByRole("dialog", { name: "Keyboard shortcuts" });
    await expect(help).toBeVisible();
    await expect(help.getByText("Move")).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(help).toBeHidden();

    const nav = page.getByRole("navigation", { name: "Main" });
    await page.keyboard.press("[");
    await expect(nav).toBeHidden();
    await page.getByRole("button", { name: "Show sidebar" }).click();
    await expect(nav).toBeVisible();
    watch.expectNoErrors();
  });

  test("the user menu switches theme and language", async ({ page }) => {
    const watch = watchErrors(page);
    await open(page, "/dashboard");
    const account = page.getByRole("button", { name: /Repody Operator|no sign-in|sans connexion/ });
    await account.click();
    const menu = page.getByRole("menu");
    await menu.getByRole("radio", { name: "Dark" }).click();
    await expect(page.locator("html")).toHaveClass(/dark/);
    await menu.getByRole("radio", { name: "Light" }).click();
    await expect(page.locator("html")).not.toHaveClass(/dark/);
    await menu.getByRole("menuitemradio", { name: "Français" }).click();
    await expect(page.getByRole("heading", { level: 1, name: "Vue d'ensemble" })).toBeVisible();
    // Radio items keep the menu open, so the second choice is one click away.
    await menu.getByRole("menuitemradio", { name: "English" }).click();
    await expect(page.getByRole("heading", { level: 1, name: "Overview" })).toBeVisible();
    watch.expectNoErrors();
  });

  test("unknown pages, runs and workflows show the not-found screen", async ({ page }) => {
    for (const path of ["/does-not-exist", "/audits/run-missing", "/workflows/wf-missing/edit"]) {
      const response = await page.goto(path);
      expect(response?.status(), path).toBe(404);
      await expect(page.getByRole("heading", { name: "Nothing here" })).toBeVisible();
    }
    await page.getByRole("link", { name: "Runs" }).last().click();
    await expect(page).toHaveURL(/\/audits$/);
  });
});
