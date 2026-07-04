# Client deployment kit

YAML templates and ExternalSecret examples for **client production** clusters.  
Install steps live in [docs/deploy/CLIENT.md](../../docs/deploy/CLIENT.md).  
Vendor → client image flow: [docs/deploy/VENDOR-TO-CLIENT.md](../../docs/deploy/VENDOR-TO-CLIENT.md).

## Choose a profile

| Profile | When | Start here |
|---------|------|------------|
| **External** | Client has managed Postgres, Redis, S3 | `values-external.example.yaml` |
| **Bundled** | In-cluster Postgres, Redis, MinIO | `values-bundled.example.yaml` + `bundled/values.data.yaml` |

Both profiles merge `values-enterprise.example.yaml` for production hardening.

## Image registry convention

`REPODY_IMAGE_REGISTRY` and Helm `images.*.repository` use the **Harbor project path**:

```yaml
# CHANGE_ME_REGISTRY = harbor.client.example.com/repody   (host + project)
images:
  api:
    repository: harbor.client.example.com/repody/repody-backend
    tag: "1.0.0"
```

Build/push uses the same base:

```powershell
$env:REPODY_IMAGE_REGISTRY="harbor.client.example.com/repody"
$env:REPODY_IMAGE_TAG="1.0.0"
pnpm images:release
```

Official Harbor push/pull: [Harbor docs — working with images](https://goharbor.io/docs/main/working-with-projects/working-with-images/pulling-pushing-images/)

## Directory layout

```
deploy/client/
├── values-external.example.yaml    # BYO Postgres / Redis / S3
├── values-bundled.example.yaml     # In-cluster data plane
├── values-enterprise.example.yaml  # Hardening overlay (required prod)
├── namespace.example.yaml          # Namespace + Pod Security
├── argocd.application.yaml         # Argo CD Application skeleton
├── secrets/                        # ExternalSecret examples → Vault
│   ├── registry-pull.externalsecret.example.yaml
│   ├── data-plane.externalsecret.example.yaml
│   ├── runtime.externalsecret.example.yaml          # external profile
│   └── runtime-bundled.externalsecret.example.yaml  # bundled profile
├── bundled/
│   └── values.data.yaml            # repody-data chart overlay
└── lab/                            # Vendor QA only — not for clients
```

## Helm install order (bundled)

1. Namespace + secrets ([SECRETS.md](../../docs/deploy/SECRETS.md))
2. `helm upgrade --install repody-data …`
3. Optional `repody-auth` (Keycloak lab)
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
