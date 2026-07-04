# Air-gap deployment

Air-gap bundles contain the Repody platform images and Helm chart. They do not contain
or deploy inference, databases, Redis/Valkey, object storage, or an IdP.
Operate those as approved enterprise platform services, then point Repody at them
through Helm values and `repody-runtime-secrets`.

## Bundle Contents

- `repody-backend` (API and worker roles)
- `repody-web`
- `deploy/helm/repody`
- Helm dependencies
- image checksums and metadata

Bundled local infrastructure images are excluded by default.

## Build

```bash
pnpm airgap:build -- --version X.Y.Z
```

The air-gap builder creates the local `repody-backend:X.Y.Z` and `repody-web:X.Y.Z`
images itself, saves them into the bundle, and does not push to a registry.

## Import

Load platform images into the target registry, then install with Helm:

```bash
pnpm airgap:import -- --bundle ./repody-airgap-X.Y.Z --registry registry.internal.example.com/repody
```

Set image repositories in `my-values.yaml` to the internal registry:

```yaml
images:
  backend:
    repository: registry.internal.example.com/repody/repody-backend
    tag: X.Y.Z
  api:
    repository: registry.internal.example.com/repody/repody-backend
    tag: X.Y.Z
  worker:
    repository: registry.internal.example.com/repody/repody-backend
    tag: X.Y.Z
  web:
    repository: registry.internal.example.com/repody/repody-web
    tag: X.Y.Z
```

Then install:

```bash
helm upgrade --install repody ./charts/repody-0.1.0.tgz \
  -n repody --create-namespace \
  -f my-values.yaml
```

Required inference values:

```yaml
config:
  inferenceMode: vllm
  vllmBaseUrl: https://vlm.internal.example.com/v1
  vllmServedModel: numind/NuExtract3

workerOcr:
  warmupOnStart: false

externalRedis:
  enabled: true
  existingSecret: repody-runtime-secrets
  urlKey: AUDIT_REDIS_URL
```

If the internal inference endpoint requires auth, create `repody-runtime-secrets`
with `AUDIT_VLLM_API_KEY`. The same Secret must contain data-plane credentials and
`AUDIT_REDIS_URL`.

## Inference Responsibility

The regulated environment should approve and operate its own inference runtime:

- vLLM on a GPU node pool
- llama-server on CPU/GPU infrastructure
- a managed or shared OpenAI-compatible endpoint

Repody only needs network access to `/v1/models` and `/v1/chat/completions`.
