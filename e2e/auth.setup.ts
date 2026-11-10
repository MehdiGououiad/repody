import { type APIRequestContext, expect, test as setup } from "@playwright/test";
import {
  fetchKeycloakToken,
  fetchOidcEnabled,
  loginViaKeycloak,
  writeAuthArtifacts,
} from "./helpers/auth";
import { API_URL, WEB_URL } from "./helpers/env";
import { ensureSeedData } from "./helpers/seed";

/**
 * Runs before the browser projects (Playwright setup project): waits for the stack, signs in
 * once through Keycloak and saves the session the tests reuse, then seeds the demo data.
 * https://playwright.dev/docs/auth#basic-shared-account-in-all-tests
 */
setup.setTimeout(240_000);

/** Whether the URL answers 2xx; a refused or reset connection (still starting) is a no. */
async function answers(request: APIRequestContext, url: string): Promise<boolean> {
  return request.get(url).then(
    (response) => response.ok(),
    () => false
  );
}

setup("stack is up", async ({ request }) => {
  await expect
    .poll(() => answers(request, `${API_URL}/v1/healthz`), { timeout: 180_000 })
    .toBe(true);
  await expect.poll(() => answers(request, `${WEB_URL}/login`), { timeout: 180_000 }).toBe(true);
});

setup("sign in and seed", async ({ page }) => {
  if (await fetchOidcEnabled()) {
    const token = await fetchKeycloakToken();
    await loginViaKeycloak(page, "/dashboard");
    writeAuthArtifacts(token, JSON.stringify(await page.context().storageState(), null, 2));
  } else {
    // Without Keycloak there is no session; tests still load the (empty) storage state.
    writeAuthArtifacts("", JSON.stringify({ cookies: [], origins: [] }));
  }
  await ensureSeedData();
});
