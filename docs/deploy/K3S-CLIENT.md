# k3s client cluster (bundled profile)

Simulate a **real client** on upstream k3s (via [k3d](https://k3d.io/)) using the same bundled install path as production — no OpenShift Routes, no host-network inference hacks.

Official references:

- [k3d](https://k3d.io/stable/)
- [Kubernetes Ingress](https://kubernetes.io/docs/concepts/services-networking/ingress/)
- [External Secrets — Vault](https://external-secrets.io/latest/provider/hashicorp-vault/)
- [OpenTelemetry Collector Helm chart](https://github.com/open-telemetry/opentelemetry-helm-charts)

## What this proves

| Practice | How |
|----------|-----|
| Secrets outside Git | Vault KV → ESO → `repody-runtime-secrets` |
| Bundled data plane | `repody-data` chart (Postgres, Redis, MinIO) |
| Portable edge | `networking.k8s.io/v1` Ingress (Traefik) |
| Hardening | `values-enterprise.example.yaml` |
| Observability | OTEL collector in `observability` namespace |
| Images | Private registry + `registry-pull-secret` |

## Prerequisites

- Docker Desktop
- `k3d`, `kubectl`, `helm`, `openssl`
- ~12 GiB RAM free

```powershell
winget install k3d.k3d
pnpm doctor
```

## Full deploy

```powershell
pnpm k3s:client
```

Steps (automatic): clean cluster → k3d registry → Vault + ESO → seed → OTEL → `pnpm images:release` → Helm (data → auth → app) → verify.

Add to `C:\Windows\System32\drivers\etc\hosts` (admin) when prompted:

```
127.0.0.1 app.repody.test api.repody.test auth.repody.test files.repody.test
```

## URLs

| Service | URL |
|---------|-----|
| Web | https://app.repody.test:8443 |
| API | https://api.repody.test:8443/v1/healthz/live |
| Auth | https://auth.repody.test:8443 |
| Files | https://files.repody.test:8443 |

Traefik is mapped to host port **8443** (not 443) so the lab does not conflict with other TLS listeners on Windows.

## Inference (client-managed)

Production keeps VLM **outside** the Repody chart ([REPODY-VLM.md](../REPODY-VLM.md)). For extraction tests, point at your client endpoint:

```powershell
$env:REPODY_VLM_URL="https://your-vlm.example.com/v1"
node deploy/scripts/k3s-client-bundled.mjs deploy
```

Or run host `pnpm llamacpp:serve` only for local dev — not part of the k3s client contract.

## Teardown

```powershell
pnpm k3s:client:clean
```

## Manual steps

```powershell
node deploy/scripts/k3s-client-bundled.mjs preflight
node deploy/scripts/k3s-client-bundled.mjs cluster
node deploy/scripts/k3s-client-bundled.mjs bootstrap
node deploy/scripts/k3s-client-bundled.mjs seed
node deploy/scripts/k3s-client-bundled.mjs observability
node deploy/scripts/k3s-client-bundled.mjs images
node deploy/scripts/k3s-client-bundled.mjs deploy
node deploy/scripts/k3s-client-bundled.mjs verify
```

## vs OpenShift CRC

| | k3s client lab | OpenShift CRC |
|--|----------------|---------------|
| Edge | Ingress (Traefik) | Ingress (default) |
| Registry | k3d local registry | CRC internal registry |
| IdP | `repody-auth` + Ingress | same |
| Use when | Generic K8s client proof | OpenShift-specific QA |

Production client guide: [CLIENT.md](./CLIENT.md)
