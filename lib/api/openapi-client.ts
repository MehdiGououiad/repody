import createClient from "openapi-fetch";
import { formatApiError } from "@/lib/api/api-error";
import type { paths } from "@/lib/api/generated/schema";
import { guardSessionResponse } from "@/lib/api/http";

/** Browser client: hits the Next.js `/api` rewrite, where Proxy adds the session token. */
function createBrowserOpenApiClient() {
  const client = createClient<paths>({ baseUrl: "/api" });
  client.use({
    async onResponse({ request, response }) {
      await guardSessionResponse(response, new URL(request.url).pathname);
      return response;
    },
  });
  return client;
}

export const browserApi = createBrowserOpenApiClient();

export function throwOnApiError(
  error: unknown,
  response: Response,
  fallback = `HTTP ${response.status}`
): never {
  const text = typeof error === "string" ? error : error != null ? JSON.stringify(error) : "";
  throw new Error(formatApiError(text) || fallback);
}
