# Pinned versions

Repody pins patch-level image tags and dependency floors for reproducible deploys.
Production values must not use `latest` image tags or bundled local infrastructure.

Canonical local/dev image env file: [`deploy/pinned-images.env`](../deploy/pinned-images.env).

| Service | Pinned tag |
|---------|------------|
| Postgres | `postgres:17.10-alpine` |
| Redis | `redis:8.8.0-alpine` |
| MinIO | `pgsty/minio:RELEASE.2026-06-18T00-00-00Z` |
| MinIO CLI (`mc`) | `pgsty/mc:RELEASE.2026-04-17T00-00-00Z` |
| Keycloak | `quay.io/keycloak/keycloak:26.6.4` |

Enterprise production images should be promoted by immutable tag or digest from the
client registry.

## Application runtimes

| Runtime | Version |
|---------|---------|
| Python backend base | `python:3.13.14-slim` |
| Node web base | `node:24-alpine` |
| uv in Dockerfile | `0.11.26` |
| pnpm | `11.7.0` |

## Enterprise production

| Concern | Recommended source |
|---------|--------------------|
| Repody API/Web/Worker | Client registry, immutable tag or digest |
| Postgres | Managed Postgres or CloudNativePG |
| Redis/Valkey | Managed service or operator-backed deployment |
| Object storage | Enterprise S3-compatible endpoint or MinIO Operator/Tenant |
| Taskiq broker | Redis / Valkey (`AUDIT_REDIS_URL`) |
| IdP | Enterprise OIDC provider |
| Inference | External OpenAI-compatible VLM endpoint |

## Helm data plane (`repody-data`)

The bundled data chart ships **native StatefulSets** with official upstream images (no Bitnami subcharts).
Production external-profile values must point at managed Postgres, Redis/Valkey, and object storage instead.

| Workload | Image (bundled lab) | Production posture |
|----------|---------------------|--------------------|
| PostgreSQL | `postgres:17.10-alpine` | Managed Postgres or CloudNativePG |
| Redis | `redis:8.8.0-alpine` | Managed Redis/Valkey |
| MinIO | `pgsty/minio:RELEASE.2026-06-18T00-00-00Z` | External S3 or MinIO Operator/Tenant |

The main `repody` chart keeps conditional subchart slots disabled by default; bundled infra is deployed via `repody-data`.

## Supply-chain overrides

pnpm workspace overrides (see `pnpm-workspace.yaml`) pin patched transitive deps until upstream bundles them:

| Package | Reason |
|---------|--------|
| `postcss@^8.5.15` | Next.js still pulls 8.4.x ([GHSA-qx2v-qp2m-jg93](https://github.com/advisories/GHSA-qx2v-qp2m-jg93)) |
| `@opentelemetry/core@^2.8.0` | Sentry OTel exporters ([GHSA-8988-4f7v-96qf](https://github.com/advisories/GHSA-8988-4f7v-96qf)) |

## Security scanners (CI + local)

| Tool | Pinned version | Role |
|------|----------------|------|
| Trivy | `0.72.0` | Primary — fs, IaC, secrets, container images |
| Grype | `v0.110.0` | SBOM validation (Syft SPDX input) |
| Syft | `v1.40.0` | SBOM generation (shared with `pnpm release:attest`) |
| `aquasecurity/trivy-action` | `0.33.1` | GitHub Actions integration |
| `anchore/scan-action` | `v7` | Grype in CI |
| `github/codeql-action/upload-sarif` | `v3` | GitHub Security tab |

Gate: **CRITICAL + HIGH**, unfixed only (Trivy/Grype). Merged report: `dist/security/report.md`.

## Upgrading

```powershell
# Refresh Python lockfile
cd backend && uv lock --upgrade

# Refresh frontend lockfile
pnpm update --latest

# Helm data plane (bundled profile — no subchart deps)
pnpm helm:lint

# Validate enterprise Kubernetes renders
pnpm deploy:check
```

## CI

- Python 3.13
- Node 24
- pnpm 11.7.0
