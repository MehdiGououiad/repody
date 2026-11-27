/**
 * Upstream service origins for server-side calls (RSC, route proxies).
 * Prefer INTERNAL_*_API_URL (in-cluster / Compose DNS) over public/host URLs.
 * Never bake these into next.config rewrites - read at runtime only.
 */
function normalizeOrigin(raw: string | undefined): string | null {
  const trimmed = raw?.trim();
  return trimmed ? trimmed.replace(/\/+$/, "") : null;
}

export function backendOrigin(): string {
  return (
    normalizeOrigin(process.env.INTERNAL_API_URL) ??
    normalizeOrigin(process.env.BACKEND_URL) ??
    "http://127.0.0.1:8000"
  );
}

export function coreOrigin(): string | null {
  return normalizeOrigin(process.env.INTERNAL_CORE_API_URL ?? process.env.CORE_API_URL);
}

export function fraudOrigin(): string | null {
  return normalizeOrigin(process.env.INTERNAL_FRAUD_API_URL ?? process.env.FRAUD_API_URL);
}
