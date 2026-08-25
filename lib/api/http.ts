import { formatApiError } from "@/lib/api/api-error";
import { resolveAuthCredential, workflowAuthHeaders } from "@/lib/api/auth-policy";

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

/** Browser — Next.js `/api/v1` runtime proxy (credential per auth policy). */
export async function browserFetch(
  path: string,
  init?: RequestInit & { timeoutMs?: number; workflowApiKey?: string }
): Promise<Response> {
  const { timeoutMs, workflowApiKey, ...rest } = init ?? {};
  const controller = timeoutMs ? new AbortController() : null;
  const timer = controller && timeoutMs ? setTimeout(() => controller.abort(), timeoutMs) : null;
  const normalized = path.startsWith("/api") ? path : `/api${apiPath(path)}`;
  const credential = resolveAuthCredential(normalized);
  const authHeaders: HeadersInit =
    credential === "workflow" && workflowApiKey ? workflowAuthHeaders(workflowApiKey) : {};
  try {
    const res = await fetch(normalized, {
      ...rest,
      signal: controller?.signal ?? rest.signal,
      headers: {
        ...(rest.body instanceof FormData ? {} : { "content-type": "application/json" }),
        ...authHeaders,
        ...rest.headers,
      },
    });
    if (
      typeof window !== "undefined" &&
      res.status === 401 &&
      credential === "session" &&
      !window.location.pathname.startsWith("/login")
    ) {
      void redirectToLoginAfterUnauthorized();
    }
    if (typeof window !== "undefined" && res.status === 403 && credential === "session") {
      const body = await res.clone().text();
      if (body.toLowerCase().includes("forbidden") || body.toLowerCase().includes("permission")) {
        window.location.href = "/unauthorized";
      }
    }
    return res;
  } catch (err) {
    if (controller && err instanceof DOMException && err.name === "AbortError") {
      throw new Error(`Request timed out after ${Math.round(timeoutMs! / 1000)}s`);
    }
    throw err;
  } finally {
    if (timer) clearTimeout(timer);
  }
}

export async function browserJson<T>(
  path: string,
  init?: RequestInit & { timeoutMs?: number }
): Promise<T> {
  const res = await browserFetch(path, init);
  if (!res.ok) await readApiError(res, `API ${path}`);
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}
