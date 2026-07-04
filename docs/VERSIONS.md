# Pinned versions

Repody pins patch-level image tags and dependency floors for reproducible deploys.
Production values must not use `latest` image tags or bundled local infrastructure.

Canonical local/dev image env file: [`deploy/pinned-images.env`](../deploy/pinned-images.env).
Enterprise production images should be promoted by immutable tag or digest from the
client registry.

## Application runtimes

| Runtime | Version |
|---------|---------|
| Python backend base | `python:3.13.14-slim` |
| Node web base | `node:24-alpine` |
| uv in Dockerfile | `0.11.21` |
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

## Helm subcharts

The Repody chart still carries conditional subcharts for the **bundled** client profile.
They are disabled by default and production external-profile renders fail if bundled infra is enabled.

| Chart | Pinned chart version | Production posture |
|-------|----------------------|--------------------|
| Bitnami PostgreSQL | `18.7.6` | Disabled; use managed Postgres/CloudNativePG |
| Bitnami Redis | `27.0.10` | Disabled; use managed Redis/Valkey |
| Bitnami MinIO | `17.0.21` | Disabled; use external object storage |

## Upgrading

```powershell
# Refresh Python lockfile
cd backend && uv lock --upgrade

# Refresh frontend lockfile
pnpm update --latest

# Helm subcharts (bundled profile)
pnpm helm:deps

# Validate enterprise Kubernetes renders
pnpm deploy:check
```

## CI

- Python 3.13
- Node 24
- pnpm 11.7.0
