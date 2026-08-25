import "server-only";

import createClient from "openapi-fetch";
import { isOidcConfigured } from "@/auth";
import { backendOrigin } from "@/lib/api/backend-origin";
import type { paths } from "@/lib/api/generated/schema";
import { serverFetch } from "@/lib/api/http-server";
import { getServerAccessToken } from "@/lib/auth/access-token-server";

async function serverAuthHeaders(): Promise<HeadersInit> {
  if (!isOidcConfigured()) {
    return {};
  }
  const accessToken = await getServerAccessToken();
  if (!accessToken) {
    return {};
  }
  return { Authorization: `Bearer ${accessToken}` };
}

/** Server Components — calls Python API directly. */
export function createServerOpenApiClient() {
  return createClient<paths>({
    baseUrl: backendOrigin(),
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

export const serverApi = createServerOpenApiClient();
