import createClient from "openapi-fetch";
import type { paths } from "@/lib/api/generated/schema";
import { formatApiError } from "@/lib/api/api-error";

/** Browser client: hits the Next.js `/api` rewrite, where Proxy adds the session token. */
export function createBrowserOpenApiClient() {
  return createClient<paths>({ baseUrl: "/api" });
}

export const browserApi = createBrowserOpenApiClient();

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

export { browserFetch, browserJson } from "@/lib/api/http";
