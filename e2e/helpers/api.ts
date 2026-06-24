import { readApiToken } from "./auth";
import { API_URL } from "./env";

const API = API_URL;

function authHeaders(): Record<string, string> {
  const token = readApiToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export function apiAuthHeaders(extra?: Record<string, string>): Record<string, string> {
  return { ...authHeaders(), ...extra };
}

export async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${API}/v1${path}`, { headers: authHeaders() });
  if (!res.ok) throw new Error(`GET ${path} → ${res.status}`);
  return res.json() as Promise<T>;
}

export async function apiPost<T>(path: string, body?: unknown, headers?: HeadersInit): Promise<T> {
  const res = await fetch(`${API}/v1${path}`, {
    method: "POST",
    headers: { "content-type": "application/json", ...authHeaders(), ...headers },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`POST ${path} → ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

export async function pollRun(
  runId: string,
  maxAttempts = 30,
  intervalMs = 500
): Promise<{ status: string; result?: unknown; error?: string }> {
  for (let i = 0; i < maxAttempts; i++) {
    const body = await apiGet<{ status: string; result?: unknown; error?: string }>(
      `/runs/${runId}`
    );
    if (body.status === "done" || body.status === "failed") return body;
    await new Promise((r) => setTimeout(r, intervalMs));
  }
  throw new Error(`Run ${runId} did not complete in time`);
}

export { API };
