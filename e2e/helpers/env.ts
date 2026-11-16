export const WEB_URL = process.env.E2E_WEB_URL ?? "http://localhost:3000";
export const API_URL = process.env.E2E_API_URL ?? "http://localhost:8000";

export const AUTH_URL = process.env.E2E_AUTH_URL ?? "http://localhost:8080";

export const KEYCLOAK_USER = process.env.E2E_KEYCLOAK_USER ?? "operator@repody.local";
export const KEYCLOAK_PASSWORD = process.env.E2E_KEYCLOAK_PASSWORD ?? "repody-dev";
/** A read-only account: sees workflows and runs, changes nothing. */
export const KEYCLOAK_VIEWER = {
  name: process.env.E2E_KEYCLOAK_VIEWER ?? "viewer@repody.local",
  password: process.env.E2E_KEYCLOAK_VIEWER_PASSWORD ?? KEYCLOAK_PASSWORD,
};
/** Deleting workflows is admin-only (`workflow:delete`): the dev realm's admin does it. */
export const KEYCLOAK_ADMIN = {
  name: process.env.E2E_KEYCLOAK_ADMIN ?? "admin@repody.local",
  password: process.env.E2E_KEYCLOAK_ADMIN_PASSWORD ?? KEYCLOAK_PASSWORD,
};

export const AUTH_STORAGE_PATH = "e2e/.auth/operator.json";
export const API_TOKEN_PATH = "e2e/.auth/api-token.txt";
