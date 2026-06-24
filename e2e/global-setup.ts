import { chromium, type FullConfig } from "@playwright/test";
import {
  fetchKeycloakToken,
  fetchOidcEnabled,
  loginViaKeycloak,
  writeAuthArtifacts,
} from "./helpers/auth";
import { API_URL, AUTH_STORAGE_PATH, WEB_URL } from "./helpers/env";
import { ensureSeedData } from "./helpers/seed";

async function waitForOk(url: string, label: string, attempts = 90): Promise<void> {
  for (let i = 0; i < attempts; i++) {
    try {
      const res = await fetch(url, { signal: AbortSignal.timeout(5000) });
      if (res.ok) {
        console.log(`[e2e] ${label} ready at ${url}`);
        return;
      }
    } catch {
      /* retry */
    }
    await new Promise((r) => setTimeout(r, 2000));
  }
  throw new Error(`[e2e] Timed out waiting for ${label} at ${url}`);
}

export default async function globalSetup(config: FullConfig) {
  const apiURL = (config.metadata?.apiURL as string) ?? API_URL;
  const webURL = process.env.E2E_WEB_URL ?? WEB_URL;

  await waitForOk(`${apiURL}/v1/healthz`, "API");
  await waitForOk(webURL, "Web");

  const oidcEnabled = await fetchOidcEnabled();
  if (!oidcEnabled) {
    console.log("[e2e] OIDC disabled — skipping Keycloak login");
    await ensureSeedData();
    return;
  }

  console.log("[e2e] OIDC enabled — acquiring Keycloak session");
  const token = await fetchKeycloakToken();

  const browser = await chromium.launch();
  try {
    const context = await browser.newContext({ baseURL: webURL });
    const page = await context.newPage();
    await loginViaKeycloak(page, "/dashboard");
    const storageState = await context.storageState();
    writeAuthArtifacts(token, JSON.stringify(storageState, null, 2));
    console.log(`[e2e] Auth artifacts saved to ${AUTH_STORAGE_PATH}`);
  } finally {
    await browser.close();
  }

  await ensureSeedData();
  return;
}
