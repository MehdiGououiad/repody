# Kubernetes / cloud deployment

Deploy Repody on Kubernetes with Helm. This is the supported production path.

The Repody chart deploys:

- `repody-api` control plane
- `repody-worker` document and fast worker pools
- `repody-web` edge/UI

Enterprise production values do **not** deploy Postgres, Redis, MinIO, Hatchet Lite,
Keycloak, Bugsink, or inference. Those are platform services supplied by the client,
by a managed provider, or by dedicated operators.

The chart does **not** deploy inference. Run vLLM, llama-server, or a managed
OpenAI-compatible VLM separately and point `config.vllmBaseUrl` at it.

## Enterprise fit

Repody targets **any standard Kubernetes 1.28+** cluster (EKS, GKE, AKS, OpenShift, Rancher, on-prem). The chart deploys only the application plane; the client supplies managed services:

| Client provides | Repody chart consumes |
|-----------------|----------------------|
| Postgres (or CloudNativePG) | `AUDIT_DATABASE_URL` via Secret |
| Redis / Valkey | `AUDIT_REDIS_URL` |
| S3-compatible storage | `externalObjectStorage.*` |
| Hatchet | `externalHatchet.*` + `HATCHET_CLIENT_TOKEN` |
| OIDC IdP (Keycloak, Entra ID, Okta, …) | `config.oidcIssuer`, audience, CORS |
| VLM endpoint (vLLM, managed GPU) | `config.vllmBaseUrl`, `AUDIT_VLLM_API_KEY` |
| Ingress or Gateway API + TLS | `ingress.*` or `gatewayApi.*` |
| Image registry + pull secrets | `images.*`, `global.imagePullSecrets` |

Production values are guarded by `templates/enterprise-policy.yaml`: bundled Postgres, Redis, MinIO, Keycloak, and Hatchet Lite **fail the Helm render** when `global.deploymentEnvironment=production`.

Integration work per client: DNS/TLS, secrets (External Secrets / Vault), network paths from workers to VLM, and Hatchet connectivity. See [ONPREM-MANAGED-DATA.md](./ONPREM-MANAGED-DATA.md) and [deploy/argocd/README.md](../deploy/argocd/README.md).

## Prerequisites

- Kubernetes 1.28+
- `kubectl`
- `helm` 3.14+
- Container registry
- Ingress controller or Gateway API implementation
- External OpenAI-compatible VLM endpoint reachable from worker pods
- External Hatchet endpoint reachable from API and worker pods
- Managed/operator-backed Postgres, Redis/Valkey, and S3-compatible object storage

## 1. Build and push images

```bash
export REGISTRY=ghcr.io/YOUR_ORG
export TAG=0.1.0

pnpm images:build
pnpm images:push
```

Images:

| Image | Role |
|-------|------|
| `repody-api` | FastAPI control plane |
| `repody-worker` | Hatchet workers |
| `repody-web` | Next.js edge |

## 2. Fetch Helm dependencies

```bash
pnpm helm:deps
```

## 3. Configure values

```bash
cp deploy/helm/repody/values-production.yaml.example my-values.yaml
```

Required settings:

- `images.*.repository` and `images.*.tag`
- `ingress.host` or `gatewayApi.host`
- `config.oidcIssuer`
- `config.corsOrigins`
- `config.vllmBaseUrl`
- `config.vllmServedModel`
- `externalHatchet.hostPort` and `externalHatchet.serverUrl`
- `secrets.existingSecret`

External inference example:

```yaml
config:
  inferenceMode: vllm
  vllmBaseUrl: https://your-vlm-host/v1
  vllmServedModel: numind/NuExtract3

workerOcr:
  warmupOnStart: false
  resources:
    requests:
      cpu: 250m
      memory: 768Mi
    limits:
      memory: 2Gi
```

Create the runtime secret outside Git:

```bash
kubectl -n repody create secret generic repody-runtime-secrets \
  --from-literal=AUTH_SECRET="long-random-auth-secret" \
  --from-literal=AUTH_KEYCLOAK_CLIENT_SECRET="keycloak-client-secret" \
  --from-literal=AUDIT_DATABASE_URL="postgresql+asyncpg://user:pass@host:5432/audit_workbench" \
  --from-literal=AUDIT_REDIS_URL="rediss://..." \
  --from-literal=AUDIT_MINIO_ACCESS_KEY="object-storage-access-key" \
  --from-literal=AUDIT_MINIO_SECRET_KEY="object-storage-secret-key" \
  --from-literal=HATCHET_CLIENT_TOKEN="hatchet-client-token" \
  --from-literal=AUDIT_VLLM_API_KEY="external-vlm-api-key"
```

`AUDIT_VLLM_API_KEY` is optional for unauthenticated endpoints.
For production, sync this Secret from Vault, External Secrets Operator, SOPS,
Sealed Secrets, or your cloud secret manager.

## 4. Install

```bash
helm upgrade --install repody deploy/helm/repody \
  -n repody --create-namespace \
  -f deploy/helm/repody/values-production.yaml.example \
  -f deploy/helm/repody/values-production.gateway.yaml.example \
  -f my-values.yaml
```

Dry-run:

```bash
helm template repody deploy/helm/repody -f my-values.yaml
```

## 5. Verify

```bash
kubectl -n repody get pods
kubectl -n repody port-forward svc/repody-web 3000:3000
```

Verify inference from a worker pod:

```bash
kubectl -n repody exec deploy/repody-worker-ocr -- \
  sh -c 'python - <<PY
import os, urllib.request
print(urllib.request.urlopen(os.environ["AUDIT_VLLM_BASE_URL"] + "/models", timeout=10).status)
PY'
```

## Scaling

## Production hardening defaults

- Envoy Gateway production values enable HTTPS and HTTP-to-HTTPS redirects.
- API readiness uses `/v1/healthz`; liveness uses `/v1/healthz/live`.
- API, web, workers, and migration jobs do not mount service account tokens.
- NetworkPolicies default-deny pod traffic, then allow DNS, internal app traffic,
  Gateway/Ingress entry points, and configured external egress ports.
- Production values use managed/operator-backed Postgres, Redis/Valkey, object
  storage, external Hatchet, and an enterprise IdP. The chart fails production
  renders that re-enable bundled local infrastructure.
- Database migrations run as a Helm migration Job when `migrations.enabled=true`;
  API replicas do not race migrations on startup.

The chart defaults assume external inference: workers call the VLM endpoint, but do
not reserve GPU/model memory. Increase OCR memory only if PDF rasterization or page
batching shows real pressure in pod metrics.

```yaml
workerOcr:
  autoscaling:
    enabled: true
    minReplicas: 2
    maxReplicas: 20
```

```bash
helm upgrade repody deploy/helm/repody -f my-values.yaml \
  --set workerOcr.replicas=5
```

## Managed data plane

Disable in-cluster charts and point at managed services:

```yaml
postgresql:
  enabled: false
externalDatabase:
  enabled: true
  existingSecret: repody-runtime-secrets
  urlKey: AUDIT_DATABASE_URL

redis:
  enabled: false
externalRedis:
  enabled: true
  existingSecret: repody-runtime-secrets
  urlKey: AUDIT_REDIS_URL

minio:
  enabled: false
externalObjectStorage:
  enabled: true
  endpoint: s3.amazonaws.com
  bucket: my-bucket
  existingSecret: repody-runtime-secrets
  accessKeyKey: AUDIT_MINIO_ACCESS_KEY
  secretKeyKey: AUDIT_MINIO_SECRET_KEY
  publicEndpoint: files.example.com
```

For an on-prem managed Postgres baseline, see
[`ONPREM-MANAGED-DATA.md`](./ONPREM-MANAGED-DATA.md). It includes CloudNativePG,
PgBouncer, scheduled backups, NetworkPolicies, and External Secrets examples.

## Observability

- Logs: ship pod stdout to your cluster log stack. `AUDIT_LOG_JSON=true` is set by values.
- Errors: set `observability.bugsinkDsn`.
- Traces: set `observability.otelEnabled=true` and `observability.otelEndpoint`.

## Troubleshooting

| Symptom | Check |
|---------|-------|
| API stuck init | Hatchet token bootstrap job and secret |
| Workers cannot extract | Worker pod can reach `config.vllmBaseUrl` |
| 401/403 from inference | `AUDIT_VLLM_API_KEY` exists in runtime Secret |
| Upload failures | `filesHost` / `AUDIT_MINIO_PUBLIC_ENDPOINT` |
| Auth failures | OIDC issuer and JWKS URL reachable from API pods |
