# Secrets and hardening

Production **never** stores passwords, API keys, or connection strings in Helm values or Git. Clients use **External Secrets Operator** (or Sealed Secrets / SOPS) backed by **Vault**, a cloud secret manager, or equivalent.

Manifest examples: `deploy/client/secrets/` · ClusterSecretStore example: `deploy/managed/external-secrets/`

Official reference: [External Secrets — Vault provider](https://external-secrets.io/latest/provider/hashicorp-vault/)

## Required Kubernetes secrets

| Secret | Profile | Created by |
|--------|---------|------------|
| `registry-pull-secret` | both | ESO or manual bootstrap |
| `repody-runtime-secrets` | both | ESO — `runtime.externalsecret.example.yaml` or `runtime-bundled.externalsecret.example.yaml` |
| `repody-data-postgresql` | bundled | ESO — `data-plane.externalsecret.example.yaml` |
| `repody-data-redis` | bundled | ESO |
| `repody-data-minio` | bundled | ESO |

## Vault layout (example)

```
secret/repody/production/
  AUTH_SECRET
  AUTH_KEYCLOAK_CLIENT_SECRET
  KEYCLOAK_ADMIN_PASSWORD       # only if using repody-auth (lab/small tenant)
  AUDIT_DATABASE_URL            # external: RDS URL | bundled: postgresql+asyncpg://...@repody-data-postgresql:5432/...
  AUDIT_REDIS_URL               # required for Taskiq
  AUDIT_MINIO_ACCESS_KEY
  AUDIT_MINIO_SECRET_KEY
  BUGSINK_DSN
  AUDIT_VLLM_API_KEY
  REGISTRY_DOCKERCONFIGJSON     # dockerconfigjson for registry-pull-secret

secret/repody/production/data/   # bundled data-plane only
  POSTGRES_ADMIN_PASSWORD
  POSTGRES_USER_PASSWORD
  REDIS_PASSWORD
  MINIO_ROOT_USER
  MINIO_ROOT_PASSWORD
```

Adapt mount paths to match your `ClusterSecretStore` and ExternalSecret `remoteRef` blocks.

## Apply order

```bash
kubectl apply -f deploy/client/namespace.example.yaml
kubectl apply -f deploy/managed/external-secrets/vault-clustersecretstore.example.yaml  # adapt
kubectl apply -f deploy/client/secrets/registry-pull.externalsecret.example.yaml
kubectl apply -f deploy/client/secrets/runtime.externalsecret.example.yaml
# bundled only:
kubectl apply -f deploy/client/secrets/data-plane.externalsecret.example.yaml
kubectl -n repody wait externalsecret --all --for=condition=Ready --timeout=5m
```

Then install Helm charts — see [CLIENT.md](./CLIENT.md).

**OpenShift internal registry:** store pull credentials for both the external route and `image-registry.openshift-image-registry.svc:5000/...` in `REGISTRY_DOCKERCONFIGJSON`.

## Helm hardening overlay

Merge `deploy/client/values-enterprise.example.yaml` on every production install:

```bash
-f deploy/helm/repody/values-common.yaml \
-f <client-values>.yaml \
-f deploy/client/values-enterprise.example.yaml
```

This enforces:

- `platform.compatibility.restricted`
- `secrets.create: false`
- `networkPolicy.enabled: true`
- PodDisruptionBudgets and autoscaling

> `deploy/values/openshift.yaml` sets `networkPolicy.enabled: false` for minimal external smoke tests only. **Client GitOps must use `values-enterprise.example.yaml`** so network policies stay on.

## Preflight commands

**External:**

```bash
pnpm enterprise:secrets -- \
  --values deploy/helm/repody/values-common.yaml \
  --values deploy/client/values-external.example.yaml \
  --values deploy/client/values-enterprise.example.yaml \
  --external-secret deploy/client/secrets/runtime.externalsecret.example.yaml
```

**Bundled:**

```bash
pnpm enterprise:secrets -- \
  --values deploy/helm/repody/values-common.yaml \
  --values deploy/client/values-bundled.example.yaml \
  --values deploy/client/values-enterprise.example.yaml \
  --external-secret deploy/client/secrets/runtime-bundled.externalsecret.example.yaml
```

## What stays out of Git

- Database passwords, Redis auth, MinIO keys
- `AUTH_SECRET`, OIDC client secrets
- VLM API keys, Bugsink DSN
- Registry pull tokens

Only **references** (`existingSecret`, `urlKey`, Vault `remoteRef` paths) belong in values files.

## Lab vs production

| | CRC lab (`openshift-local-promote`) | Production client |
|--|-------------------------------------|-------------------|
| Vault | In-cluster dev server (fast unseal) | Client HA Vault (HTTPS) |
| ESO + paths | Same layout as production | Same |
| Secrets in Git | Never | Never |

Lab Vault overlays: `deploy/client/lab/` — see [OPENSHIFT.md](./OPENSHIFT.md#crc-lab-verification).
