#!/usr/bin/env node
/** Refresh the Keycloak API token for Playwright request helpers (run as a sync subprocess). */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { fetchKeycloakToken } from "./keycloak-token.mjs";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const tokenPath = path.join(root, process.env.E2E_API_TOKEN_PATH ?? "e2e/.auth/api-token.txt");

try {
  const token = await fetchKeycloakToken();
  fs.mkdirSync(path.dirname(tokenPath), { recursive: true });
  fs.writeFileSync(tokenPath, token, "utf8");
} catch (error) {
  console.error(error instanceof Error ? error.message : error);
  process.exit(1);
}
