import "server-only";

import createClient from "openapi-fetch";
import { backendOrigin } from "@/lib/api/backend-origin";
import type { paths } from "@/lib/api/generated/schema";
import { serverFetch } from "@/lib/api/http-server";

/** Server Components - typed client over `serverFetch` (session token + timeout). */
export const serverApi = createClient<paths>({
  baseUrl: backendOrigin(),
  fetch: async (input: Request) => {
    const url = new URL(input.url);
    return serverFetch(url.pathname + url.search, {
      method: input.method,
      headers: input.headers,
      body: input.body ? await input.arrayBuffer() : undefined,
      signal: input.signal,
    });
  },
});
