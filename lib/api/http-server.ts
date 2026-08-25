import "server-only";

import { redirect } from "next/navigation";
import { isOidcConfigured, signOut } from "@/auth";
import { backendOrigin } from "@/lib/api/backend-origin";
import { apiPath, readApiError } from "@/lib/api/http";
import { getServerAccessToken } from "@/lib/auth/access-token-server";

async function sessionAuthHeaders(): Promise<HeadersInit> {
  if (!isOidcConfigured()) {
    return {};
  }
  const accessToken = await getServerAccessToken();
  if (!accessToken) {
    return {};
  }
  return { Authorization: `Bearer ${accessToken}` };
}

/** Server Components — Python API directly (10s default timeout). */
export async function serverFetch(
  path: string,
  init?: RequestInit & { timeoutMs?: number }
): Promise<Response> {
  const { timeoutMs = 10_000, ...rest } = init ?? {};
  const controller = timeoutMs ? new AbortController() : null;
  const timer = controller && timeoutMs ? setTimeout(() => controller.abort(), timeoutMs) : null;
  const sessionHeaders = await sessionAuthHeaders();
  try {
    const res = await fetch(`${backendOrigin()}${apiPath(path)}`, {
      cache: "no-store",
      ...rest,
      signal: controller?.signal ?? rest.signal,
      headers: { ...sessionHeaders, ...rest.headers },
    });
    // Stale Keycloak JWT (e.g. realm keys rotated after Compose reset) → clear session.
    if (res.status === 401 && isOidcConfigured() && Object.keys(sessionHeaders).length > 0) {
      await signOut({ redirect: false });
      redirect("/login");
    }
    return res;
  } catch (err) {
    if (timeoutMs && err instanceof DOMException && err.name === "AbortError") {
      throw new Error(`Request timed out after ${Math.round(timeoutMs / 1000)}s`);
    }
    throw err;
  } finally {
    if (timer) clearTimeout(timer);
  }
}

export async function serverJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await serverFetch(path, init);
  if (!res.ok) await readApiError(res, `API ${path}`);
  return res.json() as Promise<T>;
}
