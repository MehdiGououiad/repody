import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import type { Page } from "@playwright/test";
import {
  API_TOKEN_PATH,
  API_URL,
  AUTH_STORAGE_PATH,
  AUTH_URL,
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

export { fetchKeycloakToken } from "./keycloak-token.mjs";

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

/** Browser login via Keycloak: Better Auth starts the OAuth flow, then the Keycloak form. */
export async function loginViaKeycloak(page: Page, callbackPath = "/dashboard"): Promise<void> {
  const signIn = await page.request.post("/api/auth/sign-in/social", {
    data: { provider: "keycloak", callbackURL: callbackPath },
    headers: { origin: new URL(WEB_URL).origin },
  });
  const { url } = signIn.ok() ? ((await signIn.json()) as { url?: string }) : {};
  if (url) {
    await page.goto(url);
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
