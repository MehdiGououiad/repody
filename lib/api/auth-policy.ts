/**
 * Central auth policy — which credential applies per API route pattern.
 *
 * Human UI: Keycloak JWT via Auth.js session (middleware + serverFetch).
 * Workflow key: deployed run API (`/api/v1/workflows/.../runs`).
 */

export type AuthCredentialKind = "session" | "workflow" | "none";

export type AuthPolicyRow = {
  pattern: RegExp;
  credential: AuthCredentialKind;
  description: string;
};

export const AUTH_POLICY: AuthPolicyRow[] = [
  {
    pattern: /^\/api\/v1\/healthz/,
    credential: "none",
    description: "Public readiness probe",
  },
  {
    pattern: /^\/api\/v1\/workflows\/[^/]+\/runs(?:\/json)?$/,
    credential: "workflow",
    description:
      "Workflow run API — workflow API key when sent; otherwise middleware injects session JWT (builder test)",
  },
  {
    pattern: /^\/api\/v1\//,
    credential: "session",
    description: "Management API — middleware injects Keycloak access token",
  },
  {
    pattern: /^\/api\//,
    credential: "session",
    description: "UI admin API — Auth.js injects Keycloak access token",
  },
  {
    pattern: /^\/v1\//,
    credential: "session",
    description: "Server-side direct backend — serverFetch session token",
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
