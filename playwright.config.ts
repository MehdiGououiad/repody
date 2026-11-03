import { existsSync } from "node:fs";
import path from "node:path";
import { defineConfig, devices } from "@playwright/test";
import { API_URL, AUTH_STORAGE_PATH, WEB_URL } from "./e2e/helpers/env";

// Defaults target the local Compose stack (pnpm platform); set E2E_* for a cluster.
const baseURL = WEB_URL;
const apiURL = API_URL;
const ignoreHTTPSErrors = process.env.E2E_IGNORE_TLS === "1" || baseURL.startsWith("https://");
const storageStatePath = path.join(process.cwd(), AUTH_STORAGE_PATH);
const storageState = existsSync(storageStatePath) ? storageStatePath : undefined;

export default defineConfig({
  testDir: "./e2e/tests",
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: [["list"], ["html", { open: "never", outputFolder: "e2e/report" }]],
  timeout: 180_000,
  expect: { timeout: 20_000 },
  globalSetup: path.join(__dirname, "e2e/global-setup.ts"),
  use: {
    baseURL,
    ignoreHTTPSErrors,
    storageState,
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
    locale: "en-US",
    extraHTTPHeaders: {
      "Accept-Language": "en-US",
    },
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  metadata: {
    apiURL,
  },
});
