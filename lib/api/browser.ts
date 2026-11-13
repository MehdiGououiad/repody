import createFetchClient from "openapi-fetch";
import createQueryClient from "openapi-react-query";
import type { paths } from "@/lib/api/generated/schema";

import { signOutToLogin } from "@/lib/auth/client";
import { openCredits } from "@/lib/playground/credits";

let signingOut = false;

/** The session ended (the API answered 401): sign out once, back here after signing in. */
function sessionEnded(): void {
  if (signingOut || window.location.pathname.startsWith("/login")) return;
  signingOut = true;
  void signOutToLogin(window.location.pathname + window.location.search);
}

/**
 * The browser's API client: `/api/v1/*` goes through the Next.js proxy, which adds the
 * session token. A 401 signs out (the session expired); a 403 shows /unauthorized; a 402 is the
 * playground declining to run or publish (it asks the visitor to contact us for credits).
 */
export const browserFetch = createFetchClient<paths>({ baseUrl: "/api" });
browserFetch.use({
  onResponse({ response }) {
    if (response.status === 401) sessionEnded();
    if (response.status === 402) openCredits();
    if (response.status === 403) {
      window.location.assign(new URL("/unauthorized", window.location.origin));
    }
    return response;
  },
});

/** Typed TanStack Query hooks for every API operation: `$api.useQuery("get", "/v1/…")`. */
export const $api = createQueryClient(browserFetch);
