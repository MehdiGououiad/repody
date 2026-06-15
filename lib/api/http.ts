import { formatApiError } from "@/lib/api/api-error";
import { resolveAuthCredential, workflowAuthHeaders } from "@/lib/api/auth-policy";

const SERVER_BASE =
  process.env.INTERNAL_API_URL ?? process.env.BACKEND_URL ?? "http://127.0.0.1:8000";

function adminHeaders(): HeadersInit {
  const token = process.env.AUDIT_ADMIN_API_TOKEN;
  if (!token) return {};
  return { Authorization: `Bearer ${token}` };
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
    return await fetch(normalized, {
      ...rest,
      signal: controller?.signal ?? rest.signal,
      headers: {
        ...(rest.body instanceof FormData ? {} : { "content-type": "application/json" }),
        ...authHeaders,
        ...rest.headers,
      },
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
  try {
    return await fetch(`${SERVER_BASE}${apiPath(path)}`, {
      cache: "no-store",
      ...rest,
      signal: controller?.signal ?? rest.signal,
      headers: { ...adminHeaders(), ...rest.headers },
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
