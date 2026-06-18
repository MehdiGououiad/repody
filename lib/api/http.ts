import { formatApiError } from "@/lib/api/api-error";
import { resolveAuthCredential, workflowAuthHeaders } from "@/lib/api/auth-policy";
import { auth, isOidcConfigured } from "@/auth";

const SERVER_BASE =
  process.env.INTERNAL_API_URL ?? process.env.BACKEND_URL ?? "http://127.0.0.1:8000";

let sessionSignOutInFlight = false;

async function redirectToLoginAfterUnauthorized(): Promise<void> {
  if (typeof window === "undefined" || sessionSignOutInFlight) return;
  if (window.location.pathname.startsWith("/login")) return;

  sessionSignOutInFlight = true;
  try {
    const { signOut } = await import("next-auth/react");
    const returnTo = encodeURIComponent(window.location.pathname + window.location.search);
    await signOut({ redirectTo: `/login?callbackUrl=${returnTo}` });
  } finally {
    sessionSignOutInFlight = false;
  }
}

async function sessionAuthHeaders(): Promise<HeadersInit> {
  if (!isOidcConfigured()) {
    return {};
  }
  const session = await auth();
  if (!session?.accessToken) {
    return {};
  }
  return { Authorization: `Bearer ${session.accessToken}` };
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

/** Browser — Next.js `/api` rewrite (credential per auth policy). */
export async function browserFetch(
  path: string,
  init?: RequestInit & { timeoutMs?: number; workflowApiKey?: string }
): Promise<Response> {
  const { timeoutMs, workflowApiKey, ...rest } = init ?? {};
  const controller = timeoutMs ? new AbortController() : null;
  const timer =
    controller && timeoutMs
      ? setTimeout(() => controller.abort(), timeoutMs)
      : null;
  const normalized = path.startsWith("/api") ? path : `/api${apiPath(path)}`;
  const credential = resolveAuthCredential(normalized);
  const authHeaders: HeadersInit =
    credential === "workflow" && workflowApiKey
      ? workflowAuthHeaders(workflowApiKey)
      : {};
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
    if (
      typeof window !== "undefined" &&
      res.status === 403 &&
      credential === "session"
    ) {
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

/** Server Components — Python API directly (10s default timeout). */
export async function serverFetch(
  path: string,
  init?: RequestInit & { timeoutMs?: number }
): Promise<Response> {
  const { timeoutMs = 10_000, ...rest } = init ?? {};
  const controller = timeoutMs ? new AbortController() : null;
  const timer =
    controller && timeoutMs
      ? setTimeout(() => controller.abort(), timeoutMs)
      : null;
  const sessionHeaders = await sessionAuthHeaders();
  try {
    return await fetch(`${SERVER_BASE}${apiPath(path)}`, {
      cache: "no-store",
      ...rest,
      signal: controller?.signal ?? rest.signal,
      headers: { ...sessionHeaders, ...rest.headers },
    });
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

export async function serverJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await serverFetch(path, init);
  if (!res.ok) await readApiError(res, `API ${path}`);
  return res.json() as Promise<T>;
}
