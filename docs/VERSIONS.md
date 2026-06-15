# Pinned versions

Repody pins **patch-level** image tags and dependency floors for reproducible deploys. We bump deliberately — not `latest` — except Hatchet Lite and vLLM where upstream publishes only rolling tags.

Canonical Compose env file: [`deploy/pinned-images.env`](../deploy/pinned-images.env).

## Container images (Compose)

| Service | Image | Notes |
|---------|-------|--------|
| Postgres (app) | `postgres:17.6-alpine` | Major bump from 16 — fresh volumes only |
| Redis | `redis:8.8.0-alpine` | Redis 8.x (Open Source) |
| MinIO | `minio/minio:RELEASE.2025-09-07T16-13-09Z` | Last widely published community image on Docker Hub |
| Hatchet Postgres | `postgres:17.6-alpine` | Same major as app DB |
| Loki / Promtail | `3.6.11` | Matched pair; **do not** use Loki 3.8+ until Alloy replaces Promtail |
| Grafana | `12.2.9` | Dashboards in `observability/grafana/` |
| Tempo | `2.9.0` | Traces profile |
## Application runtimes

| Runtime | Version |
|---------|---------|
| Python (backend image) | 3.13-slim |
| Node (web image) | 22-alpine |
| uv (in Dockerfile) | 0.11.21 |
| pnpm | 10.11.0 |

## Helm subcharts (`deploy/helm/repody`)

| Chart | Pinned chart version | App |
|-------|---------------------|-----|
| Bitnami PostgreSQL | 16.7.27 | PostgreSQL 17.x image via chart defaults |
| Bitnami Redis | 21.2.12 | Redis 8.x via `redis.image.tag` in values |
| Bitnami MinIO | 17.0.21 | MinIO |

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
- Node **22** LTS
