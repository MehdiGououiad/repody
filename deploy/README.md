# Deploy assets

Helm charts, client YAML kit, and scripts. **Documentation:** [docs/deploy/README.md](../docs/deploy/README.md)

## Quick links

| Goal | Guide | Command |
|------|-------|---------|
| Local dev | [LOCAL.md](../docs/deploy/LOCAL.md) | `pnpm dev:all` |
| Push images to registry | [VENDOR-TO-CLIENT.md](../docs/deploy/VENDOR-TO-CLIENT.md) | `pnpm images:release` |
| Client install | [CLIENT.md](../docs/deploy/CLIENT.md) | Helm / Argo CD |
| Vendor QA | [OPENSHIFT.md](../docs/deploy/OPENSHIFT.md) | `pnpm openshift:client-test` |

## Layout

| Path | Purpose |
|------|---------|
| `helm/repody` | API, web, Taskiq workers, Ingress |
| `helm/repody-data` | PostgreSQL, Redis, MinIO (bundled profile) |
| `helm/repody-auth` | Keycloak (optional) |
| `client/` | Values templates, ExternalSecrets — [client/README.md](./client/README.md) |
| `values/openshift.yaml` | OpenShift Routes overlay |
| `managed/` | CNPG, External Secrets examples |
| `registry/` | GHCR and on-prem registry notes |
| `scripts/` | Build, release, lab automation |
| `scripts/lib/` | Shared modules (`cli`, `vault-eso`, `vault-bootstrap`, `bundled-values`, `lab-seed`, `lab-tls`, `migrations-job`, `lab-security`) |

## Image registry convention

```powershell
$env:REPODY_IMAGE_REGISTRY="ghcr.io/yourorg/repody"   # host + project path
$env:REPODY_IMAGE_TAG="1.0.0"
pnpm images:release
```

Helm `images.*.repository` = `{registry}/repody-backend` (not `{registry}/repody/repody-backend` when registry already includes the project).

## Guides

| Topic | Doc |
|-------|-----|
| Index | [docs/deploy/README.md](../docs/deploy/README.md) |
| Vendor → client | [docs/deploy/VENDOR-TO-CLIENT.md](../docs/deploy/VENDOR-TO-CLIENT.md) |
| Local Compose | [docs/deploy/LOCAL.md](../docs/deploy/LOCAL.md) |
| Client install | [docs/deploy/CLIENT.md](../docs/deploy/CLIENT.md) |
| Secrets | [docs/deploy/SECRETS.md](../docs/deploy/SECRETS.md) |
| Container registry | [registry/README.md](./registry/README.md) |
| OpenShift | [docs/deploy/OPENSHIFT.md](../docs/deploy/OPENSHIFT.md) |

## Scripts

| Script | Purpose |
|--------|---------|
| `build-images.mjs` | Build and push container images |
| `release-supply-chain.mjs` | SBOM, cosign, promotion |
| `gitops-promote-staging.mjs` | Bump staging image tags in GitOps values |
| `openshift-client-test.mjs` | OpenShift client test lab (Harbor, Vault, Argo CD, OTEL) |

Shared helpers: `scripts/lib/cli.mjs`, `vault-eso.mjs`, `vault-bootstrap.mjs`, `bundled-values.mjs`, `lab-seed.mjs`, `lab-tls.mjs`, `migrations-job.mjs`.
