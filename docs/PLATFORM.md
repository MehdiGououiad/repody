# Platform architecture

Repody has one deployment path: **Kubernetes with Helm**. Local development uses the same chart on a kind cluster (`pnpm k8s:local`).

## Production modules

| Module | Kubernetes shape | Purpose |
|--------|------------------|---------|
| control | `repody-api` Deployment | Workflows, runs, uploads, dispatch |
| workers | `repody-worker-ocr`, `repody-worker-fast` Deployments | Document extraction and fast validation |
| edge | `repody-web` Deployment | Next.js UI |
| data plane | Postgres, Redis, object storage (bundled in local values; external in production) | Durable platform state |
| queue plane | Hatchet (bundled locally; external in production) | Workflow execution |
| auth | Keycloak (bundled locally; external IdP in production) | OIDC for UI and API JWT |
| inference | **External** OpenAI-compatible endpoint | Document-model VLM — not in the Repody chart |

Module catalog: [deploy/platform-modules.mjs](../deploy/platform-modules.mjs).

## Local stack

```powershell
pnpm k8s:local:hosts   # once (admin)
pnpm k8s:local         # or: pnpm dev
```

Local values (`deploy/helm/repody/values-local.yaml`) enable bundled Postgres, Redis, MinIO, Hatchet, Keycloak, Gateway API hosts (`*.repody.local`), and observability addons.

External inference for local runs (vLLM or llama-server on the host):

```powershell
$env:REPODY_VLLM_BASE_URL="http://host.docker.internal:8000/v1"
$env:REPODY_VLLM_SERVED_MODEL="nuextract3-q8_0"   # llama-server; or numind/NuExtract3 for vLLM
pnpm k8s:local
```

See [deploy/llamacpp/README.md](../deploy/llamacpp/README.md), [docs/REPODY-VLM.md](./REPODY-VLM.md), and [DEV.md](../DEV.md).

## Scale priority

1. Worker pool replicas and HPA (`workerOcr`, `workerFast`)
2. API replicas and HPA
3. Managed Postgres / Redis / object storage
4. Web replicas and ingress tuning
5. External inference capacity

## Helm values (production)

| Concern | Values |
|---------|--------|
| API scale | `api.replicas`, `api.autoscaling` |
| Worker scale | `workerOcr.*`, `workerFast.*` |
| External inference | `config.inferenceMode`, `config.vllmBaseUrl`, `config.vllmServedModel` |
| Inference auth | `AUDIT_VLLM_API_KEY` in `secrets.existingSecret` |
| External Hatchet | `externalHatchet.*`, `HATCHET_CLIENT_TOKEN` in secrets |
| OIDC | `config.oidcIssuer`, `config.oidcJwksUrl`, Keycloak or external IdP |
| Logs | `config.logJson` + cluster log collector |
| Traces | `observability.otelEnabled`, `observability.otelEndpoint` |

See [CLOUD-K8S.md](./CLOUD-K8S.md).
