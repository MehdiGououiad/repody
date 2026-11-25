import { defineConfig, devices } from "@playwright/test";
import { API_URL, AUTH_STORAGE_PATH, WEB_URL } from "./e2e/helpers/env";

// Defaults target the local Compose stack (bun run platform); set E2E_* for a cluster.
const ignoreHTTPSErrors = process.env.E2E_IGNORE_TLS === "1" || WEB_URL.startsWith("https://");

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: [["list"], ["html", { open: "never", outputFolder: "e2e/report" }]],
  timeout: 180_000,
  expect: { timeout: 20_000 },
  use: {
    baseURL: WEB_URL,
    ignoreHTTPSErrors,
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
    locale: "en-US",
    extraHTTPHeaders: { "Accept-Language": "en-US" },
  },
  projects: [
    // Signs in once and seeds the demo data; every browser project starts from its session.
    { name: "setup", testMatch: /auth\.setup\.ts/ },
    {
      name: "chromium",
      testDir: "./e2e/tests",
      dependencies: ["setup"],
      use: { ...devices["Desktop Chrome"], storageState: AUTH_STORAGE_PATH },
    },
  ],
  metadata: { apiURL: API_URL },
});
