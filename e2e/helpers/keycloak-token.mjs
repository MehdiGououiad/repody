/**
 * An access token for API calls made by tests and scripts: the `repody-e2e` service account
 * (OAuth client credentials grant; it has the operator role). One implementation for Playwright
 * helpers and `scripts/run-platform-e2e.mjs`; settings come from the E2E_* environment.
 * Browser sign-in (auth.setup.ts) uses the operator user instead.
 */
export const keycloakSettings = {
  authURL: (process.env.E2E_AUTH_URL ?? "http://localhost:8080").replace(/\/$/, ""),
  clientId: process.env.E2E_KEYCLOAK_CLIENT_ID ?? "repody-e2e",
  clientSecret: process.env.E2E_KEYCLOAK_CLIENT_SECRET ?? "repody-e2e-dev-secret",
};

/** @returns {Promise<string>} */
export async function fetchKeycloakToken() {
  const { authURL, clientId, clientSecret } = keycloakSettings;
  const response = await fetch(`${authURL}/realms/repody/protocol/openid-connect/token`, {
    method: "POST",
    headers: {
      "content-type": "application/x-www-form-urlencoded",
      // RFC 6749 §2.3.1: client credentials in HTTP Basic auth.
      authorization: `Basic ${btoa(`${encodeURIComponent(clientId)}:${encodeURIComponent(clientSecret)}`)}`,
    },
    body: new URLSearchParams({ grant_type: "client_credentials" }),
    signal: AbortSignal.timeout(15_000),
  });
  if (!response.ok) {
    throw new Error(`Keycloak token request failed (${response.status}): ${await response.text()}`);
  }
  const json = await response.json();
  if (!json.access_token) throw new Error("Keycloak token response has no access_token");
  return json.access_token;
}
