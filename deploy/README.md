# Deploy assets

Helm charts, client YAML kit, and scripts. **Documentation:** [docs/deploy/README.md](../docs/deploy/README.md)

## Quick links

| Goal | Guide | Command |
|------|-------|---------|
| Local dev | [LOCAL.md](../docs/deploy/LOCAL.md) | `pnpm dev:all` |
| Push images to Harbor | [VENDOR-TO-CLIENT.md](../docs/deploy/VENDOR-TO-CLIENT.md) | `pnpm images:release` |
| Client install | [CLIENT.md](../docs/deploy/CLIENT.md) | Helm / Argo CD |
| Vendor QA labs | [K3S-CLIENT.md](../docs/deploy/K3S-CLIENT.md), [ENTERPRISE-GITOPS.md](../docs/deploy/ENTERPRISE-GITOPS.md) | `pnpm k3s:client`, `pnpm enterprise:lab` |

## Layout

| Path | Purpose |
|------|---------|
| `helm/repody` | API, web, Taskiq workers, Ingress |
| `helm/repody-data` | PostgreSQL, Redis, MinIO (bundled profile) |
| `helm/repody-auth` | Keycloak (optional) |
| `client/` | Values templates, ExternalSecrets — [client/README.md](./client/README.md) |
| `values/openshift.yaml` | OpenShift Routes overlay |
| `managed/` | CNPG, External Secrets examples |
| `harbor/` | Harbor `harbor.yml.example` |
| `scripts/` | Build, release, lab automation |
| `scripts/lib/` | Shared modules (`cli`, `vault-eso`, `vault-bootstrap`, `bundled-values`, `lab-seed`, `lab-tls`, `migrations-job`, `lab-security`) |

## Image registry convention

```powershell
$env:REPODY_IMAGE_REGISTRY="harbor.example.com/repody"   # host + Harbor project
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
| Harbor | [docs/deploy/HARBOR.md](../docs/deploy/HARBOR.md) |
| OpenShift | [docs/deploy/OPENSHIFT.md](../docs/deploy/OPENSHIFT.md) |

## Scripts

| Script | Purpose |
|--------|---------|
| `build-images.mjs` | Build and push container images |
| `release-supply-chain.mjs` | SBOM, cosign, promotion |
| `gitops-promote-staging.mjs` | Bump staging image tags in GitOps values |
| `k3s-client-bundled.mjs` | k3d bundled client lab |
| `enterprise-gitops-lab.mjs` | Harbor + Gitea + Argo CD lab |
| `openshift-local-promote.mjs` | OpenShift CRC lab |

Shared helpers: `scripts/lib/cli.mjs`, `vault-eso.mjs`, `vault-bootstrap.mjs`, `bundled-values.mjs`, `lab-seed.mjs`, `lab-tls.mjs`, `migrations-job.mjs`.
