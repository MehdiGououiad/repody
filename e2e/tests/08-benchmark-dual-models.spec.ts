import { expect, test } from "@playwright/test";
import { API, apiAuthHeaders, apiGet } from "../helpers/api";
import { REPODY_VLM_CATALOG_ID, SURYA_OCR2_CATALOG_ID } from "../../lib/document-model-branding";

test.describe.configure({ timeout: 300_000 });

test("benchmarks UI runs Repody VLM and Surya OCR in parallel", async ({ page, request }) => {
  const statusRes = await request.get(`${API}/v1/operator/status`, {
    headers: apiAuthHeaders(),
  });
  expect(statusRes.ok()).toBeTruthy();
  const { actionsEnabled } = (await statusRes.json()) as { actionsEnabled: boolean };
  test.skip(!actionsEnabled, "Operator actions disabled on API");

  const catalog = await apiGet<{
    models: Array<{ id: string; label: string; available?: boolean; kind: string }>;
  }>("/models/catalog");

  const benchmarkModels = catalog.models.filter(
    (model) => model.kind === "document_model" || model.kind === "ocr_compare",
  );
  const repody = benchmarkModels.find((model) => model.id === REPODY_VLM_CATALOG_ID);
  const surya = benchmarkModels.find((model) => model.id === SURYA_OCR2_CATALOG_ID);
  expect(repody, "Repody VLM missing from catalog").toBeTruthy();
  expect(surya, "Surya OCR 2 missing from catalog").toBeTruthy();
  expect(repody?.available !== false, "Repody VLM not available").toBeTruthy();
  expect(surya?.available !== false, "Surya OCR 2 not available").toBeTruthy();

  await page.goto("/settings?tab=benchmarks");
  await expect(page.getByRole("heading", { name: "Run benchmark suite" })).toBeVisible();

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
  const suryaCheckbox = page.getByRole("checkbox", { name: /Surya OCR 2/ });
  await expect(repodyCheckbox).toBeVisible();
  await expect(suryaCheckbox).toBeVisible();
  if (!(await repodyCheckbox.isChecked())) await repodyCheckbox.check();
  if (!(await suryaCheckbox.isChecked())) await suryaCheckbox.check();

  const runButton = page.getByRole("button", { name: "Run benchmark" });
  await expect(runButton).toBeEnabled();
  await runButton.click();

  await expect(page.getByRole("button", { name: "Benchmark running" })).toBeVisible({
    timeout: 15_000,
  });
  await expect(page.getByRole("button", { name: "Run benchmark" })).toBeVisible({
    timeout: 240_000,
  });

  await expect(page.getByRole("heading", { name: "Benchmark report" })).toBeVisible({
    timeout: 30_000,
  });

  const reportTable = page.locator("table").filter({ hasText: "Model" });
  await expect(reportTable.getByText("surya-ocr2")).toBeVisible();
  await expect(reportTable.getByText("repody-vlm")).toBeVisible();
  await expect(reportTable.getByText("surya:ocr2")).toBeVisible();
  await expect(reportTable.getByText("repody:vlm")).toBeVisible();

  const passedBadges = reportTable.getByText("passed", { exact: true });
  await expect(passedBadges).toHaveCount(2);

  await expect(page.getByText("Text preview", { exact: false }).first()).toBeVisible();
});
