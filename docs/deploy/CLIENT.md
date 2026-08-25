# Client production install

Install Repody on the client's Kubernetes or OpenShift cluster.

**OpenShift start-to-finish:** [OPENSHIFT.md](./OPENSHIFT.md)  
**Vendor shipped images:** [VENDOR-TO-CLIENT.md](./VENDOR-TO-CLIENT.md)  
**Secrets before Helm:** [SECRETS.md](./SECRETS.md)

This page details profiles, Ingress, and Argo skeletons. Prefer OPENSHIFT.md for the ordered install on OpenShift.

## Profiles

| Profile | When | Values template |
|---------|------|-----------------|
| **External** (default) | Client has managed Postgres, Redis/Valkey, S3 | `deploy/client/values-external.example.yaml` |
| **Bundled** | In-cluster Postgres, Redis, MinIO via `repody-data` | `deploy/client/values-bundled.example.yaml` |

Both profiles merge (same on OpenShift and generic Kubernetes):

```
values.yaml (chart)
  → values-common.yaml
  → client values.yaml     (from external|bundled template)
  → enterprise.yaml        (from values-enterprise.example.yaml)
```

Copy templates to a **private GitOps repo** — never commit real hostnames or secrets.

Networking / egress is owned by the platform team — chart NetworkPolicy stays off by default.
Image digests are optional (`helm-images.yaml` from release).

## Web → API (runtime proxy)

The web Deployment sets `INTERNAL_API_URL` / `BACKEND_URL` to
`http://<release>-api:8000` at runtime. Next.js proxies browser `/api/v1/*`
through `app/api/v1/[...path]` — the same image works on Compose (`http://api:8000`)
and Kubernetes without bake-time rewrites.

OIDC: set public `config.oidcIssuer` for browser JWTs; set `config.oidcJwksUrl`
(and optionally `config.oidcInternalIssuer`) to in-cluster Keycloak Service DNS
so API JWKS fetch and Auth.js well-known calls do not depend on the public
ingress hostname. Helm derives `AUTH_KEYCLOAK_INTERNAL_ISSUER` from
`oidcJwksUrl` when `oidcInternalIssuer` is empty.

Inference URLs (`llamacppBaseUrl`, `paddleocrV6BaseUrl`, `qwen35BaseUrl`) must be
cluster-reachable — never `host.docker.internal`.

## Edge (portable Ingress)

Repody uses **standard Kubernetes Ingress** (`networking.k8s.io/v1`) only — same manifests on OpenShift, EKS, GKE, and on-prem. Chart OpenShift `Route` CRs are not used.

Set in client values:

```yaml
ingress:
  enabled: true
  host: app.client.example.com
  apiHost: api.client.example.com
  filesHost: files.client.example.com   # bundled profile
  tls:
    enabled: false            # default until you have a cert
    secretName: repody-tls    # set enabled: true when Secret exists
```

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
  --values deploy/client/values-images.example.yaml \
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
cp deploy/client/values-enterprise.example.yaml ~/repody-gitops/enterprise.yaml
# Edit: images.* repositories/tags, external*, oidc, llamacppBaseUrl, ingress hosts
```

### 3. Helm install

```bash
pnpm helm:deps:update

helm upgrade --install repody deploy/helm/repody -n repody --create-namespace \
  -f deploy/helm/repody/values.yaml \
  -f deploy/helm/repody/values-common.yaml \
  -f ~/repody-gitops/values.yaml \
  -f ~/repody-gitops/enterprise.yaml \
  --wait --timeout 25m
```

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
  -f ~/repody-gitops/values.yaml \
  -f ~/repody-gitops/enterprise.yaml \
  --wait --timeout 25m
```

### 3. Verify

```bash
pnpm client:check
curl -fsS https://<api-host>/v1/healthz/live
```

---

## Argo CD

Example Application: `deploy/client/argocd.application.yaml` (replace `CHANGE_ME_*`).
Same Application on OpenShift and generic Kubernetes.

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

Give clients: registry URL, immutable tag, chart path `deploy/helm/repody`, and [OPENSHIFT.md](./OPENSHIFT.md).

---

## Production hardening (`values-enterprise.example.yaml`)

Always merge this overlay:

- `platform.compatibility.restricted` — non-root, drop `ALL` capabilities
- `secrets.create: false`
- `networkPolicy.enabled: false` by default on OpenShift — platform team owns NetworkPolicy / egress
- PodDisruptionBudgets and autoscaling on API / web / workers

Namespace labels: `deploy/client/namespace.example.yaml` uses **restricted** Pod Security on all enforce/audit/warn.

---

## Troubleshooting

| Symptom | Check |
|---------|-------|
| API stuck in init | `AUDIT_REDIS_URL` in runtime secret; worker pods running |
| Workers cannot extract | Worker pods reach `config.llamacppBaseUrl` ([REPODY-VLM.md](../REPODY-VLM.md)) |
| 401 from inference | `AUDIT_LLAMACPP_API_KEY` in runtime secret |
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
| `deploy/client/argocd.application.yaml` | Argo CD Application skeleton (all clusters) |
