# Security

## Reporting a vulnerability

Report vulnerabilities privately through GitHub: **Security → Report a vulnerability** on this
repository ([private vulnerability reporting](https://docs.github.com/code-security/security-advisories/guidance-on-reporting-and-writing-information-about-vulnerabilities/privately-reporting-a-security-vulnerability)).
Please do not open a public issue. Include the affected version or commit, the steps to
reproduce, and the impact you observed.

## Supported versions

| Version | Supported |
|---------|-----------|
| 1.x | Yes |
| 0.x | No |

## How the platform is protected

| Area | What is in place | Where |
|------|------------------|-------|
| Sign-in | Keycloak (OIDC, PKCE) through Better Auth; the session and tokens live in encrypted, HTTP-only cookies, refreshed server-side | `lib/auth/`, `proxy.ts` |
| API access | Keycloak access tokens verified with the realm JWKS (RS256, issuer, audience, `typ: Bearer`); workflow API keys stored as SHA-256 hashes, compared in constant time, shown once | `backend/src/repody/infra/auth.py` |
| Permissions | Role-based (`viewer`, `operator`, `admin`), checked on every route | `backend/src/repody/api/deps.py` |
| Uploads | Size and count limits; a file's type is what PDFium or Pillow can open, not its name or declared type | `backend/src/repody/app/runs.py`, `extraction/render.py` |
| Input | Every request body is a bounded Pydantic model; unknown template types and impossible rules are refused on save | `backend/src/repody/schemas/` |
| Abuse | Runs per minute per API key or user (sliding window), a queue cap | `backend/src/repody/app/runs.py` |
| Exports | CSV cells that a spreadsheet would run as formulas are escaped (OWASP) | `backend/src/repody/app/runs.py` |
| Secrets | Settings hold secrets as `SecretStr` (never in logs or error reports); deployments read them from a Secret (External Secrets / Vault) | `backend/src/repody/settings.py`, `deploy/client/secrets/` |
| Containers | Non-root users, images pinned by digest, base images upgraded at build | `backend/Dockerfile`, `Dockerfile.web`, `compose.yaml` |
| Supply chain | Locked dependencies; Dependabot for every ecosystem; Trivy in CI scans both lockfiles, secrets, IaC and the built images (CRITICAL/HIGH fail); actions pinned to commit SHAs | `.github/` |

The Compose stack and the Keycloak realm in `deploy/keycloak/` are for local development only:
they use fixed demo credentials and must never be exposed to a network.
