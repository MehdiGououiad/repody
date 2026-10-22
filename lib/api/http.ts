import { formatApiError } from "@/lib/api/api-error";
import { resolveAuthCredential, workflowAuthHeaders } from "@/lib/api/auth-policy";
import { fetchWithTimeout, type TimedRequestInit } from "@/lib/api/fetch-with-timeout";

let sessionSignOutInFlight = false;

async function redirectToLoginAfterUnauthorized(): Promise<void> {
  if (typeof window === "undefined" || sessionSignOutInFlight) return;
  if (window.location.pathname.startsWith("/login")) return;

  sessionSignOutInFlight = true;
  try {
    const { signOut: clientSignOut } = await import("next-auth/react");
    const returnTo = encodeURIComponent(window.location.pathname + window.location.search);
    await clientSignOut({ redirectTo: `/login?callbackUrl=${returnTo}` });
  } finally {
    sessionSignOutInFlight = false;
  }
}

export function apiPath(path: string): string {
  if (path.startsWith("/v1/")) return path;
  if (path.startsWith("/")) return `/v1${path}`;
  return `/v1/${path}`;
}

export async function readApiError(res: Response, label: string): Promise<never> {
  const text = await res.text();
  const detail = formatApiError(text) || `HTTP ${res.status}`;
  throw new Error(`${label}: ${detail}`);
}

/** Browser - Next.js `/api/v1` runtime proxy (credential per auth policy). */
export async function browserFetch(
  path: string,
  init?: TimedRequestInit & { workflowApiKey?: string }
): Promise<Response> {
  const { workflowApiKey, ...rest } = init ?? {};
  const normalized = path.startsWith("/api") ? path : `/api${apiPath(path)}`;
  const credential = resolveAuthCredential(normalized);
  const authHeaders: HeadersInit =
    credential === "workflow" && workflowApiKey ? workflowAuthHeaders(workflowApiKey) : {};
  const res = await fetchWithTimeout(normalized, {
    ...rest,
    headers: {
      ...(rest.body instanceof FormData ? {} : { "content-type": "application/json" }),
      ...authHeaders,
      ...rest.headers,
    },
  });
  if (typeof window !== "undefined" && credential === "session") {
    if (res.status === 401) void redirectToLoginAfterUnauthorized();
    if (res.status === 403) {
      const body = (await res.clone().text()).toLowerCase();
      if (body.includes("forbidden") || body.includes("permission")) {
        window.location.assign(new URL("/unauthorized", window.location.origin).href);
      }
    }
  }
  return res;
}

export async function browserJson<T>(path: string, init?: TimedRequestInit): Promise<T> {
  const res = await browserFetch(path, init);
  if (!res.ok) await readApiError(res, `API ${path}`);
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}
