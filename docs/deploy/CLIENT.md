# Client production install

Install Repody on **the client's** Kubernetes or OpenShift cluster. Same Helm charts as vendor QA; secrets and endpoints are client-owned.

**Vendor shipped images?** Start with [VENDOR-TO-CLIENT.md](./VENDOR-TO-CLIENT.md) (registry push → pull secret → Helm/Argo).

**Security first:** [SECRETS.md](./SECRETS.md) — apply before Helm.

**OpenShift:** add `-f deploy/values/openshift.yaml` and follow [OPENSHIFT.md](./OPENSHIFT.md#production-client).

## Profiles

| Profile | When | Values template |
|---------|------|-----------------|
| **External** (default) | Client has managed Postgres, Redis/Valkey, S3 | `deploy/client/values-external.example.yaml` |
| **Bundled** | In-cluster Postgres, Redis, MinIO via `repody-data` | `deploy/client/values-bundled.example.yaml` |

Both profiles merge:

```
values.yaml (chart)
  → values-common.yaml
  → client values.yaml (from template above)
  → values-enterprise.example.yaml   ← required for production
```

Copy templates to a **private GitOps repo** — never commit real hostnames or secrets.

## Edge (portable Ingress)

Repody uses **standard Kubernetes Ingress** (`networking.k8s.io/v1`) — the same API on OpenShift, EKS, GKE, and on-prem.

Set in client values:

```yaml
ingress:
  enabled: true
  host: app.client.example.com
  apiHost: api.client.example.com
  filesHost: files.client.example.com   # bundled profile
  tls:
    enabled: true
    secretName: repody-tls
```

On OpenShift, merge `deploy/values/openshift.yaml` (adds `route.openshift.io/termination: edge` for the platform ingress controller).

Workloads are standard `apps/v1` Deployment + `v1` Service. Export plain YAML with `helm template … | kubectl apply -f -`.

## Preflight

```bash
pnpm client:check
pnpm deploy:check
```

Validate secrets layout:

```bash
pnpm enterprise:secrets -- \
  --values deploy/helm/repody/values-common.yaml \
  --values deploy/client/values-external.example.yaml \
  --values deploy/client/values-enterprise.example.yaml \
  --external-secret deploy/client/secrets/runtime.externalsecret.example.yaml
```

(Bundled: swap `values-bundled.example.yaml` and `runtime-bundled.externalsecret.example.yaml`.)

---

## External profile (BYO services)

Client runs **only** the `repody` chart. Postgres, Redis, object storage, IdP, and VLM are external.

### 1. Namespace and secrets

```bash
kubectl apply -f deploy/client/namespace.example.yaml
kubectl apply -f deploy/managed/external-secrets/vault-clustersecretstore.example.yaml  # adapt Vault URL
kubectl apply -f deploy/client/secrets/registry-pull.externalsecret.example.yaml
kubectl apply -f deploy/client/secrets/runtime.externalsecret.example.yaml
kubectl -n repody wait externalsecret --all --for=condition=Ready --timeout=5m
```

Populate Vault paths before applying ExternalSecrets. Full key list: [SECRETS.md](./SECRETS.md).

### 2. Client values

```bash
cp deploy/client/values-external.example.yaml ~/repody-gitops/values.yaml
# Edit: images.*, externalDatabase, externalRedis, externalObjectStorage,
#       config.oidcIssuer, config.vllmBaseUrl, ingress or gatewayApi hosts
```

### 3. Helm install

```bash
pnpm helm:deps:update

helm upgrade --install repody deploy/helm/repody -n repody --create-namespace \
  -f deploy/helm/repody/values.yaml \
  -f deploy/helm/repody/values-common.yaml \
  -f ~/repody-gitops/values.yaml \
  -f deploy/client/values-enterprise.example.yaml \
  --wait --timeout 25m
```

On OpenShift, also pass `-f deploy/values/openshift.yaml`.

### 4. Verify

```bash
curl -fsS https://<api-host>/v1/healthz/live
kubectl -n repody get pods
```

From a worker pod, confirm VLM reachability (see [REPODY-VLM.md](../REPODY-VLM.md)).

---

## Bundled profile (in-cluster data plane)

Postgres, Redis, and MinIO run in namespace `repody` via `repody-data`. Taskiq uses `AUDIT_REDIS_URL` from `repody-runtime-secrets` pointing at that Redis service.

| | Bundled | External |
|--|---------|----------|
| Data plane | `repody-data` chart | Client RDS / ElastiCache / S3 |
| Job queue | Taskiq over in-cluster Redis | Client Redis / Valkey |
| Secrets | Vault → ESO (same as external) | Vault → ESO |
| Charts installed | `repody-data` + `repody` | `repody` only |

**IdP:** bundled does **not** include Keycloak by default — set `config.oidcIssuer` to the organization's IdP. Optional: `repody-auth` chart for lab or small tenants.

### 1. Secrets

Apply all ExternalSecrets from [SECRETS.md](./SECRETS.md#required-kubernetes-secrets):

- `registry-pull.externalsecret.example.yaml`
- `data-plane.externalsecret.example.yaml`
- `runtime-bundled.externalsecret.example.yaml`

```bash
kubectl -n repody wait externalsecret --all --for=condition=Ready --timeout=5m
```

Ensure Vault `AUDIT_REDIS_URL` targets the Redis service created by `repody-data` (e.g. `redis://repody-data-redis-master.repody.svc:6379`).

### 2. Helm install (order matters)

```bash
helm upgrade --install repody-data deploy/helm/repody-data -n repody --create-namespace \
  -f deploy/helm/repody-data/values.yaml \
  -f deploy/client/bundled/values.data.yaml

helm upgrade --install repody deploy/helm/repody -n repody \
  -f deploy/helm/repody/values.yaml \
  -f deploy/helm/repody/values-common.yaml \
  -f deploy/client/values-bundled.example.yaml \
  -f deploy/client/values-enterprise.example.yaml \
  --wait --timeout 25m
```

On OpenShift: add `-f deploy/values/openshift.yaml` to the **repody** install.

### 3. Verify

```bash
pnpm client:check
curl -fsS https://<api-host>/v1/healthz/live
```

---

## Argo CD

Example Application: `deploy/client/argocd.application.yaml` (replace `CHANGE_ME_*`).

```yaml
valueFiles:
  - values-common.yaml
  - $values/values.yaml              # client repo
  - values-enterprise.example.yaml
```

**Bundled:** use separate Applications — sync `repody-data` before `repody`.

---

## Vendor → client handoff

| Role | Delivers | Does not deploy |
|------|----------|-----------------|
| **Vendor** | Images in GHCR / client registry + Helm charts in Git | Client cluster |
| **Client** | Cluster, Vault/ESO, private values, Helm/GitOps | Build images |

Vendor release lane: [RELEASE.md](./RELEASE.md).

```powershell
$env:REPODY_IMAGE_REGISTRY="ghcr.io/yourorg/repody"
$env:REPODY_IMAGE_TAG="1.0.0"
pnpm images:release
pnpm release:attest
```

Give clients: registry URL, immutable tag, chart path `deploy/helm/repody`, and this guide.

**Lab verification** (vendor only): OpenShift CRC — [OPENSHIFT.md](./OPENSHIFT.md#crc-lab-verification).

---

## Production hardening (`values-enterprise.example.yaml`)

Always merge this overlay:

- `platform.compatibility.restricted` — non-root, drop `ALL` capabilities
- `secrets.create: false`
- `networkPolicy.enabled: true`
- PodDisruptionBudgets and autoscaling on API / web / workers

Namespace labels: `deploy/client/namespace.example.yaml` uses **restricted** Pod Security on all enforce/audit/warn.

---

## Troubleshooting

| Symptom | Check |
|---------|-------|
| API stuck in init | `AUDIT_REDIS_URL` in runtime secret; worker pods running |
| Workers cannot extract | Worker pods reach `config.vllmBaseUrl` ([REPODY-VLM.md](../REPODY-VLM.md)) |
| 401 from inference | `AUDIT_VLLM_API_KEY` in runtime secret |
| Upload failures | `filesHost` / public object-storage endpoint |
| Auth failures | OIDC issuer and JWKS reachable from API pods |
| Helm render fails in production | Bundled Postgres/Redis/MinIO disabled — use external or bundled **profile** values correctly |

Managed Postgres on-prem: [ONPREM-MANAGED-DATA.md](../ONPREM-MANAGED-DATA.md).

---

## File reference

| File | Purpose |
|------|---------|
| `deploy/client/values-external.example.yaml` | BYO Postgres / Redis / S3 |
| `deploy/client/values-bundled.example.yaml` | In-cluster data plane |
| `deploy/client/values-enterprise.example.yaml` | Hardening overlay |
| `deploy/client/bundled/values.data.yaml` | `repody-data` overlay for bundled |
| `deploy/client/secrets/` | ExternalSecret examples |
| `deploy/client/namespace.example.yaml` | Namespace + PSA labels |
| `deploy/client/argocd.application.yaml` | Argo CD Application skeleton |
