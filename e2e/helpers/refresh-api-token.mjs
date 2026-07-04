#!/usr/bin/env node
/** Refresh Keycloak API token for Playwright request helpers (sync subprocess). */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const tokenPath = path.join(root, process.env.E2E_API_TOKEN_PATH ?? "e2e/.auth/api-token.txt");

const authURL = (process.env.E2E_AUTH_URL ?? "http://127.0.0.1:8080").replace(/\/$/, "");
const body = new URLSearchParams({
  grant_type: "password",
  client_id: process.env.E2E_KEYCLOAK_CLIENT_ID ?? "repody-web",
  client_secret: process.env.E2E_KEYCLOAK_CLIENT_SECRET ?? "repody-web-dev-secret",
  username: process.env.E2E_KEYCLOAK_USER ?? "operator@repody.local",
  password: process.env.E2E_KEYCLOAK_PASSWORD ?? "repody-dev",
});

const res = await fetch(`${authURL}/realms/repody/protocol/openid-connect/token`, {
  method: "POST",
  headers: { "content-type": "application/x-www-form-urlencoded" },
  body,
});

if (!res.ok) {
  console.error(`Keycloak token refresh failed: ${res.status}`);
  process.exit(1);
}

const json = await res.json();
if (!json.access_token) {
  console.error("Keycloak response missing access_token");
  process.exit(1);
}

fs.mkdirSync(path.dirname(tokenPath), { recursive: true });
fs.writeFileSync(tokenPath, json.access_token, "utf8");
