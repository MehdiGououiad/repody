import { expect, test } from "@playwright/test";

const API = process.env.E2E_API_URL ?? "http://localhost:8000";

test("operator console exposes live models, benchmarks, and diagnostics", async ({
  page,
  request,
}) => {
  const statusRes = await request.get(`${API}/v1/operator/status`);
  expect(statusRes.ok()).toBeTruthy();
  const actionsEnabled = (await statusRes.json()).actionsEnabled as boolean;

  await page.goto("/settings");

  await expect(page.getByRole("heading", { name: "Operator Console" })).toBeVisible();
  await expect(page.getByText("Effective runtime configuration")).toBeVisible();

  await page.getByRole("tab", { name: "Models" }).click();
  await expect(page.getByRole("heading", { name: "Model inventory" })).toBeVisible();
  await expect(page.getByText("Repody VLM")).toBeVisible();
  const warmUp = page.getByRole("button", { name: "Warm up" }).first();
  await expect(warmUp).toBeVisible();
  if (actionsEnabled) {
    await expect(warmUp).toBeEnabled();
  } else {
    await expect(warmUp).toBeDisabled();
  }

  await page.getByRole("tab", { name: "Benchmarks" }).click();
  await expect(page.getByRole("heading", { name: "Run benchmark suite" })).toBeVisible();
  const runBenchmark = page.getByRole("button", { name: "Run benchmark" });
  await expect(runBenchmark).toBeVisible();
  if (actionsEnabled) {
    await expect(runBenchmark).toBeEnabled();
  } else {
    await expect(runBenchmark).toBeDisabled();
  }

  await page.getByRole("tab", { name: "Diagnostics" }).click();
  await expect(page.getByRole("heading", { name: "System checks" })).toBeVisible();
  await expect(page.getByText("Queue dispatch")).toBeVisible();
});

test("operator console remains usable on a mobile viewport", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/settings?tab=benchmarks");

  await expect(page.getByRole("heading", { name: "Operator Console" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Run benchmark suite" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Run benchmark" })).toBeVisible();

  const horizontalOverflow = await page.evaluate(
    () => document.documentElement.scrollWidth > document.documentElement.clientWidth
  );
  expect(horizontalOverflow).toBeFalsy();
});
