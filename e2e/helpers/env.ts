export const WEB_URL = process.env.E2E_WEB_URL ?? "http://app.repody.local";
export const API_URL = process.env.E2E_API_URL ?? "http://api.repody.local";

export const AUTH_URL = process.env.E2E_AUTH_URL ?? "http://auth.repody.local";

export const KEYCLOAK_USER = process.env.E2E_KEYCLOAK_USER ?? "operator@repody.local";
export const KEYCLOAK_PASSWORD = process.env.E2E_KEYCLOAK_PASSWORD ?? "repody-dev";
export const KEYCLOAK_CLIENT_ID = process.env.E2E_KEYCLOAK_CLIENT_ID ?? "repody-web";
export const KEYCLOAK_CLIENT_SECRET =
  process.env.E2E_KEYCLOAK_CLIENT_SECRET ?? "repody-web-dev-secret";

export const AUTH_STORAGE_PATH = "e2e/.auth/operator.json";
export const API_TOKEN_PATH = "e2e/.auth/api-token.txt";