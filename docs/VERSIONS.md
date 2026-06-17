# Pinned versions

Repody pins **patch-level** image tags and dependency floors for reproducible deploys. We bump deliberately — not `latest` — except Hatchet Lite and vLLM where upstream publishes only rolling tags.

Canonical Compose env file: [`deploy/pinned-images.env`](../deploy/pinned-images.env).

## Container images (Compose)

| Service | Image | Notes |
|---------|-------|--------|
| Postgres (app) | `postgres:17.10-alpine` | Patch bump within PG 17 |
| Redis | `redis:8.8.0-alpine` | Redis 8.x (Open Source) |
| MinIO | `pgsty/minio:RELEASE.2026-04-17T00-00-00Z` | Community fork; upstream `minio/minio` archived Feb 2026 |
| Keycloak | `quay.io/keycloak/keycloak:26.6.3` | OIDC (`--with=auth`) |
| Hatchet Postgres | `postgres:17.10-alpine` | Same major as app DB |
| Loki / Promtail | `3.6.11` | Matched pair; **do not** use Loki 3.8+ until Alloy replaces Promtail |
| Grafana | `12.4.1` | Dashboards in `observability/grafana/` |
| Tempo | `2.9.2` | Traces profile (stay on 2.x until Tempo 3 GA) |
| Caddy | `2.11.4-alpine` | Public HTTPS stack |

## Application runtimes

| Runtime | Version |
|---------|---------|
| Python (backend image) | `3.13.14-slim` |
| Node (web image) | `24-alpine` (LTS) |
| uv (in Dockerfile) | `0.11.21` |
| pnpm | `11.7.0` |

## Helm subcharts (`deploy/helm/repody`)

| Chart | Pinned chart version | App |
|-------|---------------------|-----|
| Bitnami PostgreSQL | 17.1.0 | PostgreSQL 17.x image via chart defaults |
| Bitnami Redis | 23.1.1 | Redis 8.x via `redis.image.tag` in values |
| Bitnami MinIO | 17.0.23 | Final Bitnami MinIO chart (consider pgsty image for K8s) |

> Bitnami public OCI charts may lag or require a subscription after 2025. For production K8s, plan migration to official charts or Chainguard/KubeLauncher alternatives ([ADR 004](./adr/004-cloud-kubernetes-packaging.md)).

## Upgrading

```powershell
# Refresh Python lockfile
cd backend && uv lock --upgrade

# Refresh frontend lockfile
pnpm update --latest

# Helm subcharts (requires helm CLI)
pnpm helm:deps

# After Postgres major bump: wipe volumes
pnpm compose down --stack=dev -v
```

## CI

- Python **3.13** on GitHub Actions
- Node **24** LTS
- pnpm **10.34.x**
