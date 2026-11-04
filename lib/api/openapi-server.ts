import "server-only";

import { redirect } from "next/navigation";
import createClient from "openapi-fetch";
import { auth, isOidcConfigured, signOut } from "@/auth";
import { backendOrigin } from "@/lib/api/backend-origin";
import type { paths } from "@/lib/api/generated/schema";

const TIMEOUT_MS = 10_000;

/** Server Components: the API directly, with the session's Keycloak token and a timeout. */
export const serverApi = createClient<paths>({ baseUrl: backendOrigin(), cache: "no-store" });

serverApi.use({
  async onRequest({ request }) {
    const signal = AbortSignal.any([request.signal, AbortSignal.timeout(TIMEOUT_MS)]);
    const session = isOidcConfigured() ? await auth() : null;
    const token = session && !session.error ? session.accessToken : undefined;
    const headers = new Headers(request.headers);
    if (token) headers.set("Authorization", `Bearer ${token}`);
    return new Request(request, { headers, signal });
  },
  async onResponse({ request, response }) {
    // A stale token (e.g. realm keys rotated): clear the session and sign in again.
    if (response.status === 401 && request.headers.has("Authorization")) {
      await signOut({ redirect: false });
      redirect("/login");
    }
    return response;
  },
});
