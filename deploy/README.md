# Deploy assets

Helm charts, client YAML kit, and scripts. **Documentation:** [docs/LOCAL.md](../docs/LOCAL.md) (laptop) · [docs/CLUSTER.md](../docs/CLUSTER.md) (cluster).

## Quick links

| Goal | Guide | Command |
|------|-------|---------|
| Local laptop | [LOCAL.md](../docs/LOCAL.md) | `pnpm platform` |
| Push images / vendor handoff | [CLUSTER.md](../docs/CLUSTER.md#vendor-to-client-handoff) | `pnpm images:release` |
| OpenShift / client install | [CLUSTER.md](../docs/CLUSTER.md) | Helm / Argo CD |

## Layout

| Path | Purpose |
|------|---------|
| `helm/repody` | API, web, Taskiq workers, Ingress |
| `helm/repody-data` | PostgreSQL, Redis, MinIO (bundled profile) |
| `helm/repody-auth` | Keycloak (optional) |
| `client/` | Values templates, ExternalSecrets - [client/README.md](./client/README.md) |
| `managed/` | CNPG, External Secrets examples |
| `registry/` | GHCR and on-prem registry notes |
| `scripts/` | Image build, release, readiness checks |

## Image registry convention

```powershell
$env:REPODY_IMAGE_REGISTRY="ghcr.io/yourorg/repody"   # host + project path
$env:REPODY_IMAGE_TAG="1.0.0"
pnpm images:release
```

Helm `images.*.repository` = `{registry}/repody-backend` (not `{registry}/repody/repody-backend` when registry already includes the project).

Production tags must be **immutable** - never `latest`.
