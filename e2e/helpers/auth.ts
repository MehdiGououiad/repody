import fs from "fs";
import path from "path";
import { spawnSync } from "child_process";
import type { Page } from "@playwright/test";
import {
  API_TOKEN_PATH,
  API_URL,
  AUTH_STORAGE_PATH,
  AUTH_URL,
  KEYCLOAK_CLIENT_ID,
  KEYCLOAK_CLIENT_SECRET,
  KEYCLOAK_PASSWORD,
  KEYCLOAK_USER,
  WEB_URL,
} from "./env";

type Healthz = { oidcEnabled?: boolean; status?: string };

export async function fetchOidcEnabled(): Promise<boolean> {
  try {
    const res = await fetch(`${API_URL}/v1/healthz`, { signal: AbortSignal.timeout(5000) });
    if (!res.ok) return false;
    const body = (await res.json()) as Healthz;
    return Boolean(body.oidcEnabled);
  } catch {
    return false;
  }
}

export async function fetchKeycloakToken(): Promise<string> {
  const body = new URLSearchParams({
    grant_type: "password",
    client_id: KEYCLOAK_CLIENT_ID,
    client_secret: KEYCLOAK_CLIENT_SECRET,
    username: KEYCLOAK_USER,
    password: KEYCLOAK_PASSWORD,
  });

  const res = await fetch(`${AUTH_URL}/realms/repody/protocol/openid-connect/token`, {
    method: "POST",
    headers: { "content-type": "application/x-www-form-urlencoded" },
    body,
    signal: AbortSignal.timeout(15_000),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Keycloak token request failed (${res.status}): ${text}`);
  }

  const json = (await res.json()) as { access_token?: string };
  if (!json.access_token) {
    throw new Error("Keycloak token response missing access_token");
  }
  return json.access_token;
}

export function readApiToken(): string | null {
  const token = readApiTokenFromFile();
  if (!token) return null;
  if (!isApiTokenExpired(token)) return token;
  refreshApiTokenSync();
  return readApiTokenFromFile();
}

function readApiTokenFromFile(): string | null {
  try {
    const token = fs.readFileSync(path.join(process.cwd(), API_TOKEN_PATH), "utf8").trim();
    return token || null;
  } catch {
    return null;
  }
}

function decodeJwtPayload(token: string): { exp?: number } | null {
  try {
    const segment = token.split(".")[1];
    if (!segment) return null;
    const padded = segment.padEnd(segment.length + ((4 - (segment.length % 4)) % 4), "=");
    return JSON.parse(Buffer.from(padded, "base64url").toString("utf8")) as { exp?: number };
  } catch {
    return null;
  }
}

export function isApiTokenExpired(token: string, skewSeconds = 60): boolean {
  const payload = decodeJwtPayload(token);
  if (!payload?.exp) return true;
  return payload.exp * 1000 <= Date.now() + skewSeconds * 1000;
}

function refreshApiTokenSync(): void {
  const script = path.join(process.cwd(), "e2e/helpers/refresh-api-token.mjs");
  const result = spawnSync(process.execPath, [script], {
    cwd: process.cwd(),
    env: process.env,
    encoding: "utf8",
  });
  if (result.status !== 0) {
    throw new Error(result.stderr || result.stdout || "Failed to refresh API token");
  }
}

export function writeApiToken(token: string): void {
  const dir = path.join(process.cwd(), path.dirname(API_TOKEN_PATH));
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(path.join(process.cwd(), API_TOKEN_PATH), token, "utf8");
}

export function writeAuthArtifacts(token: string, storageStateJson: string): void {
  const dir = path.join(process.cwd(), path.dirname(AUTH_STORAGE_PATH));
  fs.mkdirSync(dir, { recursive: true });
  writeApiToken(token);
  fs.writeFileSync(path.join(process.cwd(), AUTH_STORAGE_PATH), storageStateJson, "utf8");
}

/** Browser login via Keycloak (Auth.js CSRF + standard login form). */
export async function loginViaKeycloak(page: Page, callbackPath = "/dashboard"): Promise<void> {
  const callbackUrl = new URL(callbackPath, WEB_URL).href;

  const csrfRes = await page.request.get("/api/auth/csrf");
  if (!csrfRes.ok()) {
    throw new Error(`Auth.js CSRF request failed (${csrfRes.status()})`);
  }
  const { csrfToken } = (await csrfRes.json()) as { csrfToken: string };

  const signInRes = await page.request.post("/api/auth/signin/keycloak", {
    form: { csrfToken, callbackUrl },
    maxRedirects: 0,
  });

  const location = signInRes.headers().location;
  if (signInRes.status() === 302 && location) {
    await page.goto(location);
  } else {
    await page.goto(`/login?callbackUrl=${encodeURIComponent(callbackPath)}`);
    const keycloakBtn = page.getByRole("button", { name: /Continue with Keycloak/i });
    await keycloakBtn.click();
    const authHost = new URL(AUTH_URL).hostname.replace(/\./g, "\\.");
    await page.waitForURL(new RegExp(authHost), { timeout: 30_000 });
  }

  const username = page.locator("#username, input[name='username']").first();
  await username.waitFor({ state: "visible", timeout: 30_000 });
  await username.fill(KEYCLOAK_USER);
  await page.locator("#password, input[name='password']").first().fill(KEYCLOAK_PASSWORD);
  await page.locator("#kc-login, input[name='login'], button[type='submit']").first().click();

  await page.waitForURL((url) => url.origin === new URL(WEB_URL).origin, {
    timeout: 60_000,
  });
}
