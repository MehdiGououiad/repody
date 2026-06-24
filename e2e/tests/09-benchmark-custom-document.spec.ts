import { expect, test } from "@playwright/test";
import path from "node:path";
import { API, apiAuthHeaders } from "../helpers/api";

test.describe.configure({ timeout: 300_000 });

test("benchmarks UI custom document shows markdown preview", async ({ page, request }) => {
  const statusRes = await request.get(`${API}/v1/operator/status`, {
    headers: apiAuthHeaders(),
  });
  expect(statusRes.ok()).toBeTruthy();
  const { actionsEnabled } = (await statusRes.json()) as { actionsEnabled: boolean };
  test.skip(!actionsEnabled, "Operator actions disabled on API");

  const fixture = path.join(
    process.cwd(),
    "e2e/fixtures/documents/Facture.pdf",
  );

  await page.goto("/settings?tab=benchmarks");
  await expect(page.getByRole("heading", { name: "Run benchmark suite" })).toBeVisible();

  await page.getByRole("checkbox", { name: /Use a custom document/i }).check();
  await page.locator('input[type="file"]').setInputFiles(fixture);

  await page.locator("#benchmark-profile").click();
  await page.getByRole("option", { name: "Vision models" }).click();
  await page.locator("#benchmark-warm-runs").fill("0");

  const cacheCheck = page.getByRole("checkbox", {
    name: /Verify extraction cache on the final repeated run/i,
  });
  if (await cacheCheck.isChecked()) {
    await cacheCheck.uncheck();
  }

  const repodyCheckbox = page.getByRole("checkbox", { name: /^Repody VLM$/ });
  if (!(await repodyCheckbox.isChecked())) await repodyCheckbox.check();

  const suryaCheckbox = page.getByRole("checkbox", { name: /Surya OCR 2/ });
  if (await suryaCheckbox.isChecked()) await suryaCheckbox.uncheck();

  await page.getByRole("button", { name: "Run benchmark" }).click();
  await expect(page.getByRole("button", { name: "Benchmark running" })).toBeVisible({
    timeout: 15_000,
  });
  await expect(page.getByRole("button", { name: "Run benchmark" })).toBeVisible({
    timeout: 240_000,
  });

  await expect(page.getByRole("heading", { name: "Benchmark report" })).toBeVisible({
    timeout: 30_000,
  });

  await expect(page.getByText("Rendered preview (NuExtract markdown)")).toBeVisible();
  await expect(page.getByText(/Total TTC|FACTURE|6000/i).first()).toBeVisible();
  await expect(page.getByText("passed", { exact: true }).first()).toBeVisible();
});
