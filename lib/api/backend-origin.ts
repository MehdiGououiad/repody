/**
 * Upstream FastAPI origin for server-side calls (RSC, route proxies).
 * Prefer INTERNAL_API_URL (in-cluster / Compose DNS) over BACKEND_URL.
 * Never bake this into next.config rewrites — read at runtime only.
 */
export function backendOrigin(): string {
  const raw =
    process.env.INTERNAL_API_URL?.trim() ||
    process.env.BACKEND_URL?.trim() ||
    "http://127.0.0.1:8000";
  return raw.replace(/\/+$/, "");
}
