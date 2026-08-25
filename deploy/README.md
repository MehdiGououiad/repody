# Deploy assets

Helm charts, client YAML kit, and scripts. **Documentation:** [docs/deploy/README.md](../docs/deploy/README.md)

## Quick links

| Goal | Guide | Command |
|------|-------|---------|
| Local dev | [LOCAL.md](../docs/deploy/LOCAL.md) | `pnpm platform` |
| Push images to registry | [VENDOR-TO-CLIENT.md](../docs/deploy/VENDOR-TO-CLIENT.md) | `pnpm images:release` |
| OpenShift / client install | [OPENSHIFT.md](../docs/deploy/OPENSHIFT.md) | Helm / Argo CD |
| Profiles & Ingress detail | [CLIENT.md](../docs/deploy/CLIENT.md) | — |

## Layout

| Path | Purpose |
|------|---------|
| `helm/repody` | API, web, Taskiq workers, Ingress |
| `helm/repody-data` | PostgreSQL, Redis, MinIO (bundled profile) |
| `helm/repody-auth` | Keycloak (optional) |
| `client/` | Values templates, ExternalSecrets — [client/README.md](./client/README.md) |
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

Production tags must be **immutable** — never `latest`.
