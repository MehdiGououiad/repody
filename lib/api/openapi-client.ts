import createClient from "openapi-fetch";
import { formatApiError } from "@/lib/api/api-error";
import { resolveAuthCredential } from "@/lib/api/auth-policy";
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

/** Session calls: a 401 signs out, a permission 403 shows /unauthorized. */
async function guardSession(response: Response, path: string): Promise<void> {
  if (resolveAuthCredential(path) !== "session") return;
  if (response.status === 401) void signOutToLogin();
  if (response.status === 403) {
    const body = (await response.clone().text()).toLowerCase();
    if (body.includes("forbidden") || body.includes("permission")) {
      window.location.assign(new URL("/unauthorized", window.location.origin).href);
    }
  }
}

/** Browser client: hits the Next.js `/api` rewrite, where Proxy adds the session token. */
export const browserApi = createClient<paths>({ baseUrl: "/api" });
browserApi.use({
  async onResponse({ request, response }) {
    await guardSession(response, new URL(request.url).pathname);
    return response;
  },
});

/** Data of a successful openapi-fetch call; otherwise throws with the API's error message. */
export async function unwrap<T>(
  request: Promise<{ data?: T; error?: unknown; response: Response }>
): Promise<T> {
  const { data, error, response } = await request;
  if (response.ok && data !== undefined) return data;
  const text = typeof error === "string" ? error : error != null ? JSON.stringify(error) : "";
  throw new Error(formatApiError(text) || `HTTP ${response.status}`);
}
