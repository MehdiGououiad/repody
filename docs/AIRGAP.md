# Air-gap deployment

Air-gap bundles contain the Repody platform images and Helm chart. They do not contain
or deploy inference, databases, Redis/Valkey, object storage, Hatchet, or an IdP.
Operate those as approved enterprise platform services, then point Repody at them
through Helm values and `repody-runtime-secrets`.

## Bundle Contents

- `repody-api`
- `repody-worker`
- `repody-web`
- `deploy/helm/repody`
- Helm dependencies
- image checksums and metadata

Bundled local infrastructure images are excluded by default.

## Build

```bash
pnpm images:build
pnpm images:push
pnpm airgap:build -- --version X.Y.Z
```

## Import

Load platform images into the target registry, then install with Helm:

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

externalHatchet:
  enabled: true
  hostPort: hatchet-grpc.internal.example.com:443
  serverUrl: https://hatchet.internal.example.com
```

If the internal inference endpoint requires auth, create `repody-runtime-secrets`
with `AUDIT_VLLM_API_KEY`. The same Secret must contain data-plane credentials and
`HATCHET_CLIENT_TOKEN`.

## Inference Responsibility

The regulated environment should approve and operate its own inference runtime:

- vLLM on a GPU node pool
- llama-server on CPU/GPU infrastructure
- a managed or shared OpenAI-compatible endpoint

Repody only needs network access to `/v1/models` and `/v1/chat/completions`.
