/**
 * Central auth policy — which credential applies per API route pattern.
 *
 * Admin token: UI routes via Next middleware (`/api/*` except `/api/v1/*`).
 * Workflow key: deployed run API (`/api/v1/workflows/.../runs`).
 * Server admin: RSC direct backend calls (`serverFetch`).
 */

export type AuthCredentialKind = "admin" | "workflow" | "none";

export type AuthPolicyRow = {
  pattern: RegExp;
  credential: AuthCredentialKind;
  description: string;
};

export const AUTH_POLICY: AuthPolicyRow[] = [
  {
    pattern: /^\/api\/v1\/workflows\/[^/]+\/runs/,
    credential: "workflow",
    description: "Deployed workflow run API — client Bearer (workflow key)",
  },
  {
    pattern: /^\/api\/v1\//,
    credential: "workflow",
    description: "Public workflow API surface — preserve client Bearer",
  },
  {
    pattern: /^\/api\//,
    credential: "admin",
    description: "UI admin API — middleware injects AUDIT_ADMIN_API_TOKEN",
  },
  {
    pattern: /^\/v1\//,
    credential: "admin",
    description: "Server-side direct backend — serverFetch admin token",
  },
];

export function resolveAuthCredential(path: string): AuthCredentialKind {
  const normalized = path.startsWith("/") ? path : `/${path}`;
  for (const row of AUTH_POLICY) {
    if (row.pattern.test(normalized)) {
      return row.credential;
    }
  }
  return "none";
}

export function workflowAuthHeaders(apiKey: string): HeadersInit {
  return { Authorization: `Bearer ${apiKey}` };
}
