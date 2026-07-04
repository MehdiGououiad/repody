import { existsSync } from "fs";
import path from "path";
import { defineConfig, devices } from "@playwright/test";
import { AUTH_STORAGE_PATH } from "./e2e/helpers/env";

const baseURL = process.env.E2E_WEB_URL ?? "http://app.repody.local";
const apiURL = process.env.E2E_API_URL ?? "http://api.repody.local";
const ignoreHTTPSErrors =
  process.env.E2E_IGNORE_TLS === "1" || baseURL.startsWith("https://");
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
