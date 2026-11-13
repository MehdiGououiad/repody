import { expect, test } from "@playwright/test";
import { open, watchErrors } from "../helpers/ui";

test.describe("Runs", () => {
  test("status, workflow and search filters live in the URL and can be cleared", async ({
    page,
  }) => {
    const watch = watchErrors(page);
    await open(page, "/audits");
    const rows = page.locator("[data-row]");
    await expect(rows.first()).toBeVisible();

    const status = page.getByRole("radiogroup", { name: "Status" });
    await status.getByRole("radio", { name: "Passed" }).click();
    await expect(page).toHaveURL(/outcome=passed/);
    await status.getByRole("radio", { name: "All" }).click();
    await expect(page).not.toHaveURL(/outcome=/);

    await page.getByRole("button", { name: "Workflow" }).click();
    await page.getByRole("menuitemcheckbox", { name: "Factures fournisseurs" }).click();
    await expect(page).toHaveURL(/workflow=wf-invoice-audit/);
    // One workflow at a time: choosing closes the menu.
    await expect(page.getByRole("menu")).toBeHidden();
    const chip = page.getByRole("button", { name: /Factures fournisseurs/ });
    await chip.click();
    await expect(page).not.toHaveURL(/workflow=/);

    const search = page.getByPlaceholder("Search runs");
    await search.fill("zzzz-no-such-run");
    await expect(page).toHaveURL(/q=zzzz-no-such-run/);
    await expect(page.getByText("No matching runs")).toBeVisible();
    await page.getByRole("button", { name: "Clear filters" }).click();
    await expect(search).toHaveValue("");
    await expect(rows.first()).toBeVisible();
    watch.expectNoErrors();
  });

  test("Export CSV downloads the filtered runs", async ({ page }) => {
    await open(page, "/audits?outcome=passed");
    const download = page.waitForEvent("download");
    await page.getByRole("link", { name: "Export CSV" }).click();
    const file = await download;
    expect(file.suggestedFilename()).toMatch(/\.csv$/);
    const text = await (await file.createReadStream()).toArray();
    expect(Buffer.concat(text).toString().split("\n").length).toBeGreaterThan(1);
  });

  test("a report shows the document, rules lighting up fields, and goes back on Escape", async ({
    page,
    context,
  }) => {
    const watch = watchErrors(page);
    await context.grantPermissions(["clipboard-read", "clipboard-write"]);
    await open(page, "/audits?workflow=wf-invoice-audit");
    const first = page.locator("[data-row]").first();
    const href = await first.getAttribute("href");
    await first.click();
    await expect(page).toHaveURL(new RegExp(`${href}$`));
    await expect(page.getByRole("heading", { level: 1 })).toContainText("Factures fournisseurs");

    // The document: one tab per file and its first page as an image.
    await expect(page.getByRole("tab").first()).toBeVisible();
    const pageImage = page.getByRole("img", { name: /Page 1/ }).first();
    await expect(pageImage).toBeVisible();
    await expect
      .poll(() => pageImage.evaluate((img: HTMLImageElement) => img.naturalWidth))
      .toBeGreaterThan(0);

    // Pointing at a rule lights up the fields it reads.
    await page.getByText("Total TTC = HT + TVA").hover();
    await expect(page.locator("li[data-lit]").first()).toBeVisible();
    await page.getByRole("heading", { level: 1 }).hover();
    await expect(page.locator("li[data-lit]")).toHaveCount(0);

    // The raw model output opens and closes.
    const raw = page.getByRole("button", { name: /Raw model output/ }).first();
    await raw.click();
    await expect(raw).toHaveAttribute("aria-expanded", "true");
    await raw.click();
    await expect(raw).toHaveAttribute("aria-expanded", "false");

    // Copy the id.
    await page.getByRole("button", { name: "Copy the id" }).click();
    const id = href?.split("/").pop() ?? "";
    await expect.poll(() => page.evaluate(() => navigator.clipboard.readText())).toBe(id);

    // The report's CSV.
    const download = page.waitForEvent("download");
    await page.getByRole("link", { name: "CSV" }).click();
    expect((await download).suggestedFilename()).toMatch(/\.csv$/);

    await page.keyboard.press("Escape");
    await expect(page).toHaveURL(/\/audits$/);
    watch.expectNoErrors();
  });
});
