import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";

/** @param {string} value */
function unquote(value) {
  const trimmed = value.trim();
  if (
    (trimmed.startsWith('"') && trimmed.endsWith('"')) ||
    (trimmed.startsWith("'") && trimmed.endsWith("'"))
  ) {
    return trimmed.slice(1, -1);
  }
  return trimmed;
}

/** Merge repo-root `.env` / `.env.local` into a target env object (later files win). */
export function loadRepoEnv(target = process.env) {
  const env = { ...target };
  for (const file of [".env", ".env.local"]) {
    const path = join(process.cwd(), file);
    if (!existsSync(path)) continue;
    const raw = readFileSync(path, "utf8").replace(/^\uFEFF/, "");
    for (const line of raw.split(/\r?\n/)) {
      if (!line || line.startsWith("#")) continue;
      const idx = line.indexOf("=");
      if (idx < 1) continue;
      const key = line.slice(0, idx).trim();
      env[key] = unquote(line.slice(idx + 1));
    }
  }
  if (!env.AUTH_KEYCLOAK_SECRET && env.AUTH_KEYCLOAK_CLIENT_SECRET) {
    env.AUTH_KEYCLOAK_SECRET = env.AUTH_KEYCLOAK_CLIENT_SECRET;
  }
  // Auth.js must not infer callback URLs from the server bind address (0.0.0.0).
  if (!env.AUTH_URL && !env.NEXTAUTH_URL) {
    env.AUTH_URL = "http://localhost:3000";
  }
  return env;
}
