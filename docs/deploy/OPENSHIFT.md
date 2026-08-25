# Deploy Repody on OpenShift

Same charts, values, and Ingress path as generic Kubernetes.
OpenShift is just another cluster that can run this install.

**Audience:** client platform / DevOps.  
**Also read:** [CLIENT.md](./CLIENT.md) · [SECRETS.md](./SECRETS.md) · [VENDOR-TO-CLIENT.md](./VENDOR-TO-CLIENT.md)

## Official references

| Topic | Doc |
|-------|-----|
| Helm on OpenShift | [Installing a Helm chart](https://docs.openshift.com/container_platform/latest/applications/working_with_helm_charts/installing-a-helm-chart-on-openshift.html) |
| Ingress | [OpenShift Ingress / load balancing](https://docs.redhat.com/en/documentation/openshift_container_platform/4.18/html-single/ingress_and_load_balancing/index) |
| Pod security | [Pod security admission](https://docs.openshift.com/container-platform/latest/authentication/understanding-and-managing-pod-security-admission.html) |
| Kubernetes Ingress | [Ingress](https://kubernetes.io/docs/concepts/services-networking/ingress/) |
| External Secrets + Vault | [Vault provider](https://external-secrets.io/latest/provider/hashicorp-vault/) |
| Harbor registry | [Install Harbor](https://goharbor.io/docs/latest/install-config/) |

## One portable path

```
deploy/helm/repody/values.yaml
  → values-common.yaml
  → client values.yaml      (from values-external|bundled.example.yaml)
  → client enterprise.yaml  (from values-enterprise.example.yaml)
```

No OpenShift-only overlay. No chart `Route` CRs. Exposure is always
`networking.k8s.io/Ingress` with `ingress.tls.enabled: false` until you add a cert Secret.

Workloads use the same restricted securityContext everywhere (`runAsNonRoot`, no pinned UID)
so they fit Kubernetes PSA **restricted** and OpenShift **restricted-v2**.

## Steps

### 1 — Namespace

```bash
kubectl apply -f deploy/client/namespace.example.yaml
```

### 2 — Secrets

Follow [SECRETS.md](./SECRETS.md). Apply ExternalSecrets, wait until Ready, confirm
`repody-runtime-secrets` and `registry-pull-secret`.

### 3 — Client values

```bash
cp deploy/client/values-bundled.example.yaml  ~/repody-gitops/values.yaml   # or external
cp deploy/client/values-enterprise.example.yaml ~/repody-gitops/enterprise.yaml
```

Set immutable image tags, Ingress hosts, and OIDC URLs. Keep `ingress.tls.enabled: false`
until you have a real TLS Secret (then set `enabled: true` + `secretName` on every cluster the same way).

### 4 — Helm install

```bash
pnpm helm:deps:update
```

**Bundled:**

```bash
helm upgrade --install repody-data deploy/helm/repody-data -n repody --create-namespace \
  -f deploy/helm/repody-data/values.yaml \
  -f deploy/client/bundled/values.data.yaml \
  --wait --timeout 20m

# Optional in-cluster Keycloak:
# helm upgrade --install repody-auth deploy/helm/repody-auth -n repody \
#   -f deploy/helm/repody-auth/values.yaml \
#   -f ~/repody-gitops/values.auth.yaml --wait --timeout 15m

helm upgrade --install repody deploy/helm/repody -n repody \
  -f deploy/helm/repody/values.yaml \
  -f deploy/helm/repody/values-common.yaml \
  -f ~/repody-gitops/values.yaml \
  -f ~/repody-gitops/enterprise.yaml \
  --wait --timeout 25m
```

**External:** omit `repody-data`; use `values-external.example.yaml` for the app chart.

### 5 — Optional GitOps

Use `deploy/client/argocd.application.yaml` (same Application on OpenShift and elsewhere).

### 6 — Verify

```bash
kubectl -n repody get pods,ingress
curl -k https://<api-host>/v1/healthz/live   # or http:// if your ingress is plain HTTP
pnpm client:check
```

## Harbor registry

Same as any cluster: pull secret + immutable tags in values. See Harbor section history in
[registry/README.md](../../deploy/registry/README.md) and `deploy/client/values-harbor.example.yaml`.

## Checklist

- [ ] Namespace with restricted Pod Security
- [ ] Vault + ESO; ExternalSecrets Ready
- [ ] Registry pull secret; immutable image tags
- [ ] Same valueFiles as generic Kubernetes (no OpenShift-only overlay)
- [ ] Ingress hosts; TLS only when you have a shared Secret
- [ ] `/v1/healthz/live` OK
