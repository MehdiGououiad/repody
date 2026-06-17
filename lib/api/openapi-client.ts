import createClient from "openapi-fetch";
import type { paths } from "@/lib/api/generated/schema";
import { formatApiError } from "@/lib/api/api-error";
import { serverFetch } from "@/lib/api/http";
import { auth, isOidcConfigured } from "@/auth";

const SERVER_BASE =
  process.env.INTERNAL_API_URL ?? process.env.BACKEND_URL ?? "http://127.0.0.1:8000";

async function serverAuthHeaders(): Promise<HeadersInit> {
  if (!isOidcConfigured()) {
    return {};
  }
  const session = await auth();
  if (!session?.accessToken) {
    return {};
  }
  return { Authorization: `Bearer ${session.accessToken}` };
}

/** Browser client — hits Next.js `/api` rewrite (session token via middleware). */
export function createBrowserOpenApiClient() {
  return createClient<paths>({ baseUrl: "/api" });
}

/** Server Components — calls Python API directly. */
export function createServerOpenApiClient() {
  return createClient<paths>({
    baseUrl: SERVER_BASE,
      fetch: async (input: Request) => {
      const url = new URL(input.url);
      const path = url.pathname.replace(/^\/v1/, "") || "/";
      const sessionHeaders = await serverAuthHeaders();
      const headers = new Headers(input.headers);
      for (const [key, value] of Object.entries(sessionHeaders)) {
        if (typeof value === "string") {
          headers.set(key, value);
        }
      }
      return serverFetch(path, {
        method: input.method,
        headers,
        body: input.body,
        signal: input.signal,
      });
    },
  });
}

export const browserApi = createBrowserOpenApiClient();
export const serverApi = createServerOpenApiClient();

export function throwOnApiError(
  error: unknown,
  response: Response,
  fallback = `HTTP ${response.status}`
): never {
  const text =
    typeof error === "string"
      ? error
      : error != null
        ? JSON.stringify(error)
        : "";
  throw new Error(formatApiError(text) || fallback);
}

export { browserFetch, browserJson, serverFetch, serverJson } from "@/lib/api/http";
