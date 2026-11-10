export const WEB_URL = process.env.E2E_WEB_URL ?? "http://localhost:3000";
export const API_URL = process.env.E2E_API_URL ?? "http://localhost:8000";

export const AUTH_URL = process.env.E2E_AUTH_URL ?? "http://localhost:8080";

export const KEYCLOAK_USER = process.env.E2E_KEYCLOAK_USER ?? "operator@repody.local";
export const KEYCLOAK_PASSWORD = process.env.E2E_KEYCLOAK_PASSWORD ?? "repody-dev";

export const AUTH_STORAGE_PATH = "e2e/.auth/operator.json";
export const API_TOKEN_PATH = "e2e/.auth/api-token.txt";
