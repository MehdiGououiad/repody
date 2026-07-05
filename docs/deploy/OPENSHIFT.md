# OpenShift

Two paths — do not mix them:

| Path | Audience | Tools |
|------|----------|-------|
| **Production client** | Client ops | `kubectl` + `helm` + Vault/ESO ([CLIENT.md](./CLIENT.md)) |
| **Client test lab** | Vendor QA on OpenShift/CRC | `pnpm openshift:client-test` ([below](#client-test-lab)) |

Same Helm charts on OpenShift and generic Kubernetes. Edge traffic uses **standard Ingress** (`networking.k8s.io/v1`). No `oc`-specific scripts in this repo.

## Official references

- [OpenShift Ingress (standard K8s API)](https://docs.redhat.com/en/documentation/openshift_container_platform/4.18/html-single/ingress_and_load_balancing/index)
- [Kubernetes Ingress](https://kubernetes.io/docs/concepts/services-networking/ingress/)
- [Helm on OpenShift](https://docs.openshift.com/container_platform/latest/applications/working_with_helm_charts/installing-a-helm-chart-on-openshift.html)
- [Pod Security Admission](https://docs.openshift.com/container-platform/latest/authentication/understanding-and-managing-pod-security-admission.html)
- [External Secrets — Vault](https://external-secrets.io/latest/provider/hashicorp-vault/)
- [Harbor Docker Compose installer](https://goharbor.io/docs/main/install-config/run-installer-script/)
- [Harbor push/pull images](https://goharbor.io/docs/main/working-with-projects/working-with-images/pulling-pushing-images/)
- [Argo CD getting started](https://argo-cd.readthedocs.io/en/stable/getting_started/)

---

## Production client

Portable to **any** OpenShift 4.x cluster. Follow [CLIENT.md](./CLIENT.md) and [SECRETS.md](./SECRETS.md), then add the OpenShift overlay.

### 1. Namespace

```bash
kubectl apply -f deploy/client/namespace.example.yaml
```

`namespace.example.yaml` sets **restricted** Pod Security on enforce, audit, and warn.

### 2. Secrets (ESO-first)

```bash
kubectl apply -f deploy/managed/external-secrets/vault-clustersecretstore.example.yaml  # adapt
kubectl apply -f deploy/client/secrets/registry-pull.externalsecret.example.yaml
kubectl apply -f deploy/client/secrets/runtime.externalsecret.example.yaml
# bundled: also data-plane + runtime-bundled ExternalSecrets
kubectl -n repody wait externalsecret --all --for=condition=Ready --timeout=5m
```

Populate Vault before applying ExternalSecrets. Registry pull credentials: [SECRETS.md](./SECRETS.md).

### 3. Helm install

**External profile** (typical enterprise):

```bash
helm upgrade --install repody deploy/helm/repody -n repody --create-namespace \
  -f deploy/helm/repody/values.yaml \
  -f deploy/helm/repody/values-common.yaml \
  -f ~/repody-gitops/values.yaml \
  -f deploy/client/values-enterprise.example.yaml \
  -f deploy/values/openshift.yaml \
  --wait --timeout 25m
```

**Bundled profile:** install `repody-data` first — [CLIENT.md](./CLIENT.md#bundled-profile-in-cluster-data-plane).

### 4. Observability

Merge `values-enterprise.example.yaml` for **JSON logs** (`config.logJson: true`) and **OpenTelemetry** (`observability.otelEnabled: true`). Point `observability.otelEndpoint` at your collector. See [OBSERVABILITY.md](./OBSERVABILITY.md).

### 5. Smoke test

```bash
kubectl get ingress -n repody
curl -k https://<api-host>/v1/healthz/live
pnpm client:check
```

---

## Client test lab

**Goal:** end-to-end tester for the Repody **platform** on OpenShift — build → push → pull → sync → deploy → logs. Harbor and Argo CD are **independent infra** (install once); only Repody images go through the push loop.

**Tools:** `kubectl`, `helm`, `docker` (kubeconfig to OpenShift 4.x).

### E2E phases (official workflows)

| Phase | Command | Upstream docs |
|-------|---------|---------------|
| Infra (once) | `pnpm openshift:infra` | [Harbor Docker Compose](https://goharbor.io/docs/main/install-config/run-installer-script/), [Argo CD getting started](https://argo-cd.readthedocs.io/en/stable/getting_started/), [External Secrets + Vault](https://external-secrets.io/latest/provider/hashicorp-vault/) |
| Build | `node deploy/scripts/openshift-client-test.mjs build` | Docker BuildKit |
| Push | `node deploy/scripts/openshift-client-test.mjs push` | [Harbor push/pull](https://goharbor.io/docs/main/working-with-projects/working-with-images/pulling-pushing-images/) |
| Seed | `… seed` | Vault KV → ESO → `registry-pull` secret |
| Sync | `… register` then `… sync` | [argocd app sync](https://argo-cd.readthedocs.io/en/stable/user-guide/commands/argocd_app_sync/) |
| Verify + logs | `… verify` · `… logs` | [K8s logging](https://kubernetes.io/docs/concepts/cluster-administration/logging/) |

**Full run:** `pnpm openshift:client-test` (infra + platform e2e). **Fast re-test:** `pnpm openshift:e2e` after infra is up.

### Quick start (bundled + Harbor + GitOps)

```powershell
# Log in to OpenShift (kubeconfig in KUBECONFIG)
pnpm openshift:client-test
pnpm openshift:client-ready -- --profile=bundled --registry=harbor
```

Second run (skip infra, only platform):

```powershell
pnpm openshift:e2e --skip-build
```

### Profiles

| Command | Profile | Deploy mode |
|---------|---------|-------------|
| `pnpm openshift:client-test:bundled` | In-cluster data plane | GitOps (default) |
| `pnpm openshift:client-test:external` | BYO Postgres/Redis/S3 (lab simulates data) | GitOps |
| `pnpm openshift:client-test:helm` | Bundled | Direct Helm (`--helm`) |

Flags (append to any command or `node deploy/scripts/openshift-client-test.mjs all …`):

| Flag | Default | Meaning |
|------|---------|---------|
| `--profile=bundled\|external` | `bundled` | Client profile |
| `--registry=harbor\|openshift` | `harbor` | Image registry for push |
| `--helm` | off | Direct Helm instead of Argo CD |
| `--clean` | off | Tear down lab namespaces before `all` / `e2e` |
| `--skip-images` | | Reuse existing registry tags (skip push) |
| `--skip-build` | | Skip local docker build (push only) |
| `--vlm` | | Start host `llama-server` after deploy |
| `REPODY_HARBOR_CLUSTER_HOST` | `host.crc.internal:5080` | Registry host OpenShift pods use to pull (CRC) |
| `REPODY_FORCE_INFRA=1` | | Re-run Harbor Compose / Argo manifests even if running |
| `REPODY_HELM_DEPS=1` | | Force `pnpm helm:deps:update` on helm deploy |

### What the lab installs

| Component | Namespace | Independent? |
|-----------|-----------|--------------|
| Vault (dev) | `vault` | Infra — once |
| External Secrets | `external-secrets` | Infra — once |
| Harbor | Docker Compose (host) | Infra — once (`pnpm openshift:harbor` or `infra`) |
| OTEL collector | `observability` | Infra — once |
| Argo CD | `argocd` | Infra — once (official `install.yaml`) |
| Repody stack | `repody` | **Platform e2e** — build/push/sync each run |

### Step-by-step

```powershell
node deploy/scripts/openshift-client-test.mjs preflight
node deploy/scripts/openshift-client-test.mjs infra          # Harbor + Vault + ESO + OTEL + Argo CD
node deploy/scripts/openshift-client-test.mjs build
node deploy/scripts/openshift-client-test.mjs push           # docker login + push to Harbor
node deploy/scripts/openshift-client-test.mjs seed
node deploy/scripts/openshift-client-test.mjs register       # Argo CD Applications (no sync)
node deploy/scripts/openshift-client-test.mjs sync           # explicit argocd app sync
node deploy/scripts/openshift-client-test.mjs verify
node deploy/scripts/openshift-client-test.mjs logs
```

Tear down app only: `node deploy/scripts/openshift-client-test.mjs clean --app`  
Tear down infra: `node deploy/scripts/openshift-client-test.mjs clean --infra`  
Full reset: `node deploy/scripts/openshift-client-test.mjs clean`

### Lab value overlays

Committed under `deploy/client/lab/`:

- `values.lab.common.yaml` — JSON logs, OTEL, NetworkPolicies
- `values.lab.bundled.yaml` / `values.lab.external.yaml` — profile sizing
- `values.openshift-local*.yaml` — CRC ingress sizing (legacy names, still used)
- `harbor/values.yaml` — Harbor Helm lab sizing

Generated at runtime (gitignored): `deploy/client/lab/.runtime/`

### Lab vs production

| | Client test lab | Production OpenShift |
|--|-----------------|----------------------|
| Vault | In-cluster dev mode | Client HA Vault |
| Registry | Harbor or CRC internal | Client Harbor / GHCR |
| Argo CD | Optional GitOps mode | Client GitOps repo |
| OTEL | In-cluster debug exporter | Client APM backend |
| VLM | Host `llama-server` (optional) | Client GPU service |

### E2E on lab cluster

```powershell
$env:E2E_WEB_URL="https://repody-web.<apps-domain>"
$env:E2E_API_URL="https://repody-api.<apps-domain>"
$env:E2E_AUTH_URL="https://repody-auth.<apps-domain>"
$env:E2E_K8S_NAMESPACE="repody"
$env:NODE_TLS_REJECT_UNAUTHORIZED="0"
$env:E2E_IGNORE_TLS="1"
```

See [E2E.md](../E2E.md).
