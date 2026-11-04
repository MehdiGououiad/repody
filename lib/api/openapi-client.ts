import createClient from "openapi-fetch";
import { apiErrorMessage } from "@/lib/api/api-error";
import type { paths } from "@/lib/api/generated/schema";

let signOutInFlight = false;

async function signOutToLogin(): Promise<void> {
  if (signOutInFlight || window.location.pathname.startsWith("/login")) return;
  signOutInFlight = true;
  try {
    const { signOut } = await import("next-auth/react");
    const returnTo = encodeURIComponent(window.location.pathname + window.location.search);
    await signOut({ redirectTo: `/login?callbackUrl=${returnTo}` });
  } finally {
    signOutInFlight = false;
  }
}

/** Browser client: the Next.js `/api` rewrite, where Proxy adds the session token.
 * A 401 signs out; a 403 (missing permission) shows /unauthorized. */
export const browserApi = createClient<paths>({ baseUrl: "/api" });
browserApi.use({
  onResponse({ response }) {
    if (response.status === 401) void signOutToLogin();
    if (response.status === 403) {
      window.location.assign(new URL("/unauthorized", window.location.origin).href);
    }
    return response;
  },
});

/** Data of a successful openapi-fetch call; otherwise throws with the API's error message. */
export async function unwrap<T>(
  request: Promise<{ data?: T; error?: unknown; response: Response }>
): Promise<T> {
  const { data, error, response } = await request;
  if (response.ok && data !== undefined) return data;
  throw new Error(apiErrorMessage(error) || `HTTP ${response.status}`);
}
