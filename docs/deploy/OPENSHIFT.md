# OpenShift

Two audiences — do not mix them:

| Audience | Section | Command style |
|----------|---------|---------------|
| **Client production** | [Production client](#production-client) | Manual Helm + Vault/ESO ([CLIENT.md](./CLIENT.md)) |
| **Vendor CRC lab** | [CRC lab verification](#crc-lab-verification) | Optional `pnpm openshift:promote` |

Same Helm charts on OpenShift and generic Kubernetes. Edge traffic uses **standard Ingress** (`networking.k8s.io/v1`) — works on OpenShift, EKS, GKE, and on-prem.

## Official references

- [CRC — Getting started](https://docs.openshift.com/container_platform/latest/getting_started/getting_started_with_crc.html)
- [CRC networking (host access)](https://crc.dev/docs/networking/)
- [OpenShift Ingress (standard K8s API)](https://docs.redhat.com/en/documentation/openshift_container_platform/4.18/html-single/ingress_and_load_balancing/index)
- [Kubernetes Ingress](https://kubernetes.io/docs/concepts/services-networking/ingress/)
- [Helm on OpenShift](https://docs.openshift.com/container_platform/latest/applications/working_with_helm_charts/installing-a-helm-chart-on-openshift.html)
- [Pod Security Admission](https://docs.openshift.com/container-platform/latest/authentication/understanding-and-managing-pod-security-admission.html)
- [External Secrets — Vault](https://external-secrets.io/latest/provider/hashicorp-vault/)

---

## Production client

Portable to **any** OpenShift 4.x cluster. Follow [CLIENT.md](./CLIENT.md) and [SECRETS.md](./SECRETS.md), then add the OpenShift overlay.

### 1. Namespace

```bash
oc apply -f deploy/client/namespace.example.yaml
```

`namespace.example.yaml` sets **restricted** Pod Security on enforce, audit, and warn — Repody pods are built for restricted SCC (non-root, dropped capabilities). No custom SCC required for Taskiq workers.

### 2. Secrets (ESO-first)

```bash
oc apply -f deploy/managed/external-secrets/vault-clustersecretstore.example.yaml  # adapt
oc apply -f deploy/client/secrets/registry-pull.externalsecret.example.yaml
oc apply -f deploy/client/secrets/runtime.externalsecret.example.yaml
# bundled: also data-plane + runtime-bundled ExternalSecrets
oc -n repody wait externalsecret --all --for=condition=Ready --timeout=5m
```

Populate Vault before applying ExternalSecrets. Harbor/GHCR pull credentials: [SECRETS.md](./SECRETS.md).

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

### 4. Ingress and smoke test

Set hosts in client values (`ingress.host`, `ingress.apiHost`, `ingress.filesHost`). The OpenShift overlay adds `route.openshift.io/termination: edge` for TLS ([Red Hat docs](https://docs.redhat.com/en/documentation/openshift_container_platform/4.18/html-single/ingress_and_load_balancing/index)).

```bash
oc get ingress -n repody
curl -k https://<api-host>/v1/healthz/live
pnpm client:check
```

### Production checklist

| Item | Guidance |
|------|----------|
| Network policies | **On** — merge `values-enterprise.example.yaml` (overrides openshift smoke default) |
| Inference | External VLM URL in Vault — not in the app chart ([REPODY-VLM.md](../REPODY-VLM.md)) |
| IdP | Organization OIDC (`config.oidcIssuer`) — not CRC hostnames |
| Images | Harbor / client registry — not CRC internal registry |
| Redis | `AUDIT_REDIS_URL` in runtime secrets for Taskiq |

### Lab-only (do not copy to production)

| Shortcut | Why it stays in the lab |
|----------|-------------------------|
| `pnpm openshift:promote` | Automates CRC build + dev Vault |
| `deploy/client/lab/` value overlays | CRC sizing, dev Vault, single replica |
| `repody-auth` + `*.apps-crc.testing` hosts | CRC IdP convenience |
| Host `llama-server` on workstation | Dev inference — use client GPU service in prod |
| Internal HTTP JWKS to Keycloak svc | CRC TLS workaround |

Optional: enable `global.openshift.routes.enabled: true` for OpenShift-native Routes instead of Ingress.

---

## CRC lab verification

**Goal:** prove the same charts clients receive install under OpenShift security — not a daily dev loop.

**Needs ~16 GiB RAM:** `crc config set memory 16384`

### 1. Start CRC

```powershell
crc stop
crc config set memory 16384
crc start
crc oc-env | Invoke-Expression
oc login -u kubeadmin https://api.crc.testing:6443
```

Optional — reach host inference from pods ([CRC host networking](https://crc.dev/docs/networking/)):

```powershell
crc config set enable-host-network-access true
crc cleanup   # required after changing host-network-access
crc setup
crc start
```

Without host-network-access, the promote script may use the workstation LAN IP for VLM — machine-specific, not portable.

### 2. Full automated promote (vendor)

Builds images → CRC internal registry → dev Vault + ESO → bundled stack → verify:

```powershell
pnpm openshift:promote
pnpm llamacpp:serve          # host inference on :8081
pnpm openshift:client-ready
```

Step by step:

```powershell
node deploy/scripts/openshift-local-promote.mjs preflight
node deploy/scripts/openshift-local-promote.mjs clean
node deploy/scripts/openshift-local-promote.mjs registry
node deploy/scripts/openshift-local-promote.mjs images
node deploy/scripts/openshift-local-promote.mjs bootstrap
node deploy/scripts/openshift-local-promote.mjs seed
node deploy/scripts/openshift-local-promote.mjs deploy
node deploy/scripts/openshift-local-promote.mjs verify
```

Tear down: `node deploy/scripts/openshift-local-promote.mjs clean`

### 3. Manual CRC install (same outcome as promote)

Uses lab overlays under `deploy/client/lab/` — value files only; steps are in [SECRETS.md](./SECRETS.md) and [CLIENT.md](./CLIENT.md#bundled-profile-in-cluster-data-plane).

Lab overlay stack (bundled):

- `deploy/client/lab/values.openshift-local.yaml`
- `deploy/client/lab/values.openshift-local.crc.yaml` (single replica)
- `deploy/client/lab/values.openshift-local.security.yaml` (networkPolicy on)
- `deploy/client/lab/values.data.openshift-local.yaml`
- `deploy/client/lab/values.auth.openshift-local.yaml` (optional Keycloak)
- `deploy/values/openshift.yaml`

### Lab vs production

| | CRC lab | Production OpenShift |
|--|---------|-------------------|
| Vault | In-cluster dev mode | Client HA Vault |
| Registry | CRC internal | Harbor / client registry |
| Promote script | Yes | No — GitOps / Helm |
| NetworkPolicy | On (lab security overlay) | On (`values-enterprise`) |
| VLM | Host llama-server | Client GPU / managed endpoint |
| Routes | optional (`global.openshift.routes.enabled`) | Standard **Ingress** (default) |

### E2E on CRC

```powershell
$env:E2E_WEB_URL="https://repody-web.apps-crc.testing"
$env:E2E_API_URL="https://repody-api.apps-crc.testing"
$env:E2E_AUTH_URL="https://repody-auth.apps-crc.testing"
$env:E2E_K8S_NAMESPACE="repody"
$env:NODE_TLS_REJECT_UNAUTHORIZED="0"
$env:E2E_IGNORE_TLS="1"
```

See [E2E.md](../E2E.md).
