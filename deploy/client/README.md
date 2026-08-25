# Client deployment kit

YAML templates and ExternalSecret examples for **client production** clusters.

**Start-to-finish OpenShift:** [docs/deploy/OPENSHIFT.md](../../docs/deploy/OPENSHIFT.md)  
Profiles / Ingress detail: [docs/deploy/CLIENT.md](../../docs/deploy/CLIENT.md)  
Vendor → client images: [docs/deploy/VENDOR-TO-CLIENT.md](../../docs/deploy/VENDOR-TO-CLIENT.md)
## Choose a profile

| Profile | When | Start here |
|---------|------|------------|
| **External** | Client has managed Postgres, Redis, S3 | `values-external.example.yaml` |
| **Bundled** | In-cluster Postgres, Redis, MinIO | `values-bundled.example.yaml` + `bundled/values.data.yaml` |

Both profiles merge `values-enterprise.example.yaml` for production hardening.
On OpenShift, also merge `deploy/values/openshift.yaml` (chart NetworkPolicy off — cluster owns networking).

**Harbor images:** merge `values-harbor.example.yaml` (or copy its `images` / `imagePullSecrets` into GitOps values).
See [OPENSHIFT.md — Harbor registry](../../docs/deploy/OPENSHIFT.md#harbor-registry).

## Image registry

`REPODY_IMAGE_REGISTRY` and Helm `images.*.repository` use the **registry project path**:

```yaml
# CHANGE_ME_REGISTRY = ghcr.io/yourorg/repody   (host + project)
images:
  api:
    repository: ghcr.io/yourorg/repody/repody-backend
    tag: "1.0.0"
```

```powershell
$env:REPODY_IMAGE_REGISTRY="ghcr.io/yourorg/repody"
$env:REPODY_IMAGE_TAG="1.0.0"
pnpm images:release
```

Optional: pin digests from `dist/release/<tag>/helm-images.yaml` after `pnpm release:promote`.

On-prem example: `registry.example.com/repody` — see [deploy/registry/README.md](../registry/README.md).

## Directory layout

```
deploy/client/
├── values-external.example.yaml    # BYO Postgres / Redis / S3
├── values-bundled.example.yaml     # In-cluster data plane
├── values-enterprise.example.yaml  # Hardening overlay (required prod)
├── values-images.example.yaml      # Optional digest pins
├── namespace.example.yaml          # Namespace + Pod Security
├── argocd.application.yaml         # Argo CD Application skeleton
├── secrets/                        # ExternalSecret examples → Vault
│   ├── registry-pull.externalsecret.example.yaml
│   ├── data-plane.externalsecret.example.yaml
│   ├── runtime.externalsecret.example.yaml          # external profile
│   └── runtime-bundled.externalsecret.example.yaml  # bundled profile
└── bundled/
    └── values.data.yaml            # repody-data chart overlay
```

## Helm install order (bundled)

1. Namespace + secrets ([SECRETS.md](../../docs/deploy/SECRETS.md))
2. `helm upgrade --install repody-data …`
3. Optional `repody-auth` (in-cluster Keycloak)
4. `helm upgrade --install repody …`

## Helm install order (external)

1. Namespace + secrets
2. `helm upgrade --install repody …` only

## Preflight

```bash
pnpm client:check
pnpm enterprise:secrets -- \
  --values deploy/helm/repody/values-common.yaml \
  --values deploy/client/values-bundled.example.yaml \
  --values deploy/client/values-enterprise.example.yaml \
  --external-secret deploy/client/secrets/runtime-bundled.externalsecret.example.yaml
```
