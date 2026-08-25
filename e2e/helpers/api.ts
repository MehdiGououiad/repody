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

export { API };
