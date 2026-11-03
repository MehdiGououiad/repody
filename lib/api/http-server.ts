import "server-only";

import { redirect } from "next/navigation";
import { isOidcConfigured, signOut } from "@/auth";
import { backendOrigin } from "@/lib/api/backend-origin";
import { fetchWithTimeout, type TimedRequestInit } from "@/lib/api/fetch-with-timeout";
import { getServerAccessToken } from "@/lib/auth/access-token-server";

function apiPath(path: string): string {
  if (path.startsWith("/v1/")) return path;
  return path.startsWith("/") ? `/v1${path}` : `/v1/${path}`;
}

async function sessionAuthHeaders(): Promise<Record<string, string>> {
  if (!isOidcConfigured()) return {};
  const accessToken = await getServerAccessToken();
  return accessToken ? { Authorization: `Bearer ${accessToken}` } : {};
}

/** Server Components - Python API directly with the session token (10s default timeout). */
export async function serverFetch(path: string, init?: TimedRequestInit): Promise<Response> {
  const { timeoutMs = 10_000, ...rest } = init ?? {};
  const sessionHeaders = await sessionAuthHeaders();
  const headers = new Headers(rest.headers);
  for (const [key, value] of Object.entries(sessionHeaders)) headers.set(key, value);

  const res = await fetchWithTimeout(`${backendOrigin()}${apiPath(path)}`, {
    cache: "no-store",
    ...rest,
    headers,
    timeoutMs,
  });
  // Stale Keycloak JWT (e.g. realm keys rotated) -> clear the session and sign in again.
  if (res.status === 401 && Object.keys(sessionHeaders).length > 0) {
    await signOut({ redirect: false });
    redirect("/login");
  }
  return res;
}
