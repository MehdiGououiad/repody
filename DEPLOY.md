# Deployment guide

Repody deploys on **Kubernetes** (production cluster or local kind).

Repody does not deploy inference inside the production chart. Point the platform at an
external document-model endpoint: **vLLM** (reference) or **llama-server** (local GGUF).

## Production path

```powershell
pnpm images:build
pnpm images:push
pnpm helm:deps

helm upgrade --install repody deploy/helm/repody `
  -n repody --create-namespace `
  -f deploy/helm/repody/values-production.yaml.example `
  -f deploy/helm/repody/values-production.gateway.yaml.example `
  -f my-values.yaml
```

See [docs/CLOUD-K8S.md](./docs/CLOUD-K8S.md) for the full Helm workflow.
For on-prem managed Postgres and data-plane setup, see
[docs/ONPREM-MANAGED-DATA.md](./docs/ONPREM-MANAGED-DATA.md).

## Required values

```yaml
images:
  api:
    repository: ghcr.io/YOUR_ORG/repody-api
    tag: "0.1.0"
  worker:
    repository: ghcr.io/YOUR_ORG/repody-worker
    tag: "0.1.0"
  web:
    repository: ghcr.io/YOUR_ORG/repody-web
    tag: "0.1.0"

config:
  inferenceMode: vllm
  vllmBaseUrl: https://your-external-vlm-host/v1
  vllmServedModel: your-served-model-name
  oidcEnabled: true
  oidcIssuer: https://auth.yourdomain.com/realms/repody
  oidcAudience: repody-api
  keycloakClientId: repody-web
  corsOrigins: '["https://app.yourdomain.com"]'
  logJson: true

workerOcr:
  warmupOnStart: false
  resources:
    requests:
      cpu: 250m
      memory: 768Mi
    limits:
      memory: 2Gi

secrets:
  create: false
  existingSecret: repody-runtime-secrets

migrations:
  enabled: true
```

Create the runtime secret outside Git:

```powershell
kubectl -n repody create secret generic repody-runtime-secrets `
  --from-literal=AUTH_SECRET="long-random-auth-secret" `
  --from-literal=AUTH_KEYCLOAK_CLIENT_SECRET="keycloak-client-secret" `
  --from-literal=AUDIT_DATABASE_URL="postgresql+asyncpg://user:pass@host:5432/audit_workbench" `
  --from-literal=AUDIT_REDIS_URL="rediss://..." `
  --from-literal=AUDIT_MINIO_ACCESS_KEY="object-storage-access-key" `
  --from-literal=AUDIT_MINIO_SECRET_KEY="object-storage-secret-key" `
  --from-literal=HATCHET_CLIENT_TOKEN="hatchet-client-token" `
  --from-literal=AUDIT_VLLM_API_KEY="external-vlm-api-key" `
  --from-literal=BUGSINK_DSN="https://..."
```

`AUDIT_VLLM_API_KEY` is optional when the external endpoint does not require auth.
In production, create this Secret from Vault, External Secrets Operator, Sealed
Secrets, SOPS, or your cloud secret manager; do not commit literal secret values.

The OCR worker does not reserve model-hosting memory in Kubernetes. It still needs
headroom for PDF rasterization and page batching, but inference memory belongs to the
external VLM runtime.

## Inference contract

The external endpoint must expose:

- `GET /v1/models`
- `POST /v1/chat/completions`

Repody sends vision chat-completion requests with image data URLs and NuExtract-style
`chat_template_kwargs`. vLLM with `numind/NuExtract3` is the reference runtime; a
llama-server deployment can be used when it supports the same OpenAI-compatible
multimodal request shape.

## Local development

Use the local Kubernetes stack (kind + Helm):

```powershell
pnpm k8s:local:hosts
pnpm k8s:local
```

Set `REPODY_VLLM_BASE_URL` and `REPODY_VLLM_SERVED_MODEL` in your shell to point at an
external inference endpoint. See [DEV.md](./DEV.md).

## Go-live checklist

- [ ] Build and push `repody-api`, `repody-worker`, and `repody-web` images
- [ ] Runtime secret exists and contains auth/client/VLM keys
- [ ] Runtime secret is sourced from Vault/External Secrets/SOPS, not committed values
- [ ] Envoy Gateway has a TLS Secret and HTTP-to-HTTPS redirect enabled
- [ ] Managed Postgres, Redis, and object storage are reachable from pods
- [ ] External Hatchet host/URL/token are configured and reachable from API/workers
- [ ] `config.vllmBaseUrl` is reachable from worker pods
- [ ] OIDC issuer and JWKS URL work from API pods
- [ ] Storage public endpoint is reachable by browsers
- [ ] `config.logJson=true`
- [ ] Cluster log stack collects pod stdout
- [ ] `pnpm deploy:check` passes in CI with Helm installed
