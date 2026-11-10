import "server-only";

import { redirect } from "next/navigation";
import createFetchClient from "openapi-fetch";
import createQueryClient from "openapi-react-query";
import { cache } from "react";
import { ApiError, apiErrorMessage } from "@/lib/api/api-error";
import { backendOrigin } from "@/lib/api/backend-origin";
import type { paths } from "@/lib/api/generated/schema";
import { verifySession } from "@/lib/auth/dal";

const TIMEOUT_MS = 10_000;

/** Server Components: the API directly, with the session's Keycloak token and a timeout. */
const serverFetch = createFetchClient<paths>({ baseUrl: backendOrigin(), cache: "no-store" });

serverFetch.use({
  async onRequest({ request }) {
    // The proxy already refreshed the token for this request (its cookies are the fresh ones).
    const token = await verifySession();
    const forwarded = new Headers(request.headers);
    if (token) forwarded.set("Authorization", `Bearer ${token}`);
    const signal = AbortSignal.any([request.signal, AbortSignal.timeout(TIMEOUT_MS)]);
    return new Request(request, { headers: forwarded, signal });
  },
  async onResponse({ request, response }) {
    // A token the API refuses (e.g. realm keys rotated): end the session and sign in again.
    if (response.status === 401 && request.headers.has("Authorization")) redirect("/logout");
    return response;
  },
});

/**
 * Query options for server prefetching. Their query keys equal the browser's `$api` keys, so a
 * page prefetches, dehydrates, and the client components read the same cache entries.
 */
export const $server = createQueryClient(serverFetch);

async function data<T>(request: Promise<{ data?: T; error?: unknown; response: Response }>) {
  const { data, error, response } = await request;
  if (response.ok && data !== undefined) return data;
  throw new ApiError(apiErrorMessage(error) || `HTTP ${response.status}`, response.status);
}

/** The resource, or null when the API says it does not exist. Any other failure (an outage,
 * the sign-in redirect for a stale token) reaches the error boundary or Next.js. */
async function orNotFound<T>(request: Promise<T>): Promise<T | null> {
  try {
    return await request;
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) return null;
    throw error;
  }
}

export const fetchWorkflow = cache((id: string) =>
  orNotFound(
    data(serverFetch.GET("/v1/workflows/{workflow_id}", { params: { path: { workflow_id: id } } }))
  )
);

export const fetchAudit = cache((id: string) =>
  orNotFound(data(serverFetch.GET("/v1/audits/{run_id}", { params: { path: { run_id: id } } })))
);

export const fetchPlatformConfig = cache(() => data(serverFetch.GET("/v1/platform/config")));
