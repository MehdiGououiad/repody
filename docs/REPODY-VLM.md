# External document-model inference

Repody does not run inference in the production Kubernetes chart. The platform calls an
external OpenAI-compatible VLM endpoint for document extraction.

**Supported runtimes:** [vLLM](https://docs.vllm.ai/) (reference) and **llama-server**
from [llama.cpp](https://github.com/ggml-org/llama.cpp) for local GGUF.

- Repody: Kubernetes Helm chart
- Inference: external **vLLM** or **llama-server**
- Auth: optional bearer token through `AUDIT_VLLM_API_KEY`

## Platform settings

```env
AUDIT_INFERENCE_MODE=vllm
AUDIT_VLLM_BASE_URL=https://your-vlm-host/v1
AUDIT_VLLM_SERVED_MODEL=numind/NuExtract3
AUDIT_VLLM_API_KEY=

AUDIT_REPODY_VLM_TIMEOUT_SECONDS=180
AUDIT_REPODY_VLM_MAX_PAGES_PER_REQUEST=6
AUDIT_REPODY_VLM_WARMUP_ON_START=false
AUDIT_REPODY_VLM_ENABLE_THINKING=false
AUDIT_GPU_LIVE_PROBE=false
AUDIT_HEALTHZ_PROBE_INFERENCE=false
```

The `vllm` setting means "external OpenAI-compatible document-model runtime" in the
current application code.

### NuExtract generation defaults (Repody payloads)

| Mode | `enable_thinking` | `temperature` | `top_p` / `top_k` |
|------|-------------------|---------------|-------------------|
| Production extraction | `false` | `0.2` | — |
| Thinking extraction | `true` | `0.6` | `0.95` / `40` |
| Thinking markdown | `true` | `0.7` | `0.95` / `40` |

## Endpoint contract

The endpoint should expose:

```bash
curl -s https://your-vlm-host/v1/models
curl -s https://your-vlm-host/v1/chat/completions \
  -H 'Authorization: Bearer YOUR_KEY' \
  -H 'Content-Type: application/json' \
  -d '{"model":"numind/NuExtract3","messages":[{"role":"user","content":"hi"}],"max_tokens":8}'
```

Structured extraction sends image data URLs and `chat_template_kwargs.template`.
Document markdown preview, when enabled on a workflow document, sends a second request
with `chat_template_kwargs.mode: "markdown"`.

## vLLM reference command

Low-memory profile (matches Repody’s 16k context and 6-image cap):

```bash
vllm serve numind/NuExtract3 \
  --host 0.0.0.0 --port 8000 \
  --trust-remote-code \
  --limit-mm-per-prompt '{"image": 6, "video": 0}' \
  --chat-template-content-format openai \
  --generation-config vllm \
  --max-model-len 16384
```

Set `AUDIT_VLLM_SERVED_MODEL` to the id returned by `/v1/models`.

For full context on large GPUs, NuExtract documents `--max-model-len 131072` and optional
MTP speculative decoding — see [numind/NuExtract3-GGUF](https://huggingface.co/numind/NuExtract3-GGUF).

## llama-server (local GGUF)

Local Compose default: **`NuExtract3-Q4_K_M.gguf`** with served id **`nuextract3-q4_k_m`**.

```powershell
winget install llama.cpp
copy deploy\llamacpp\paths.local.env.example deploy\llamacpp\paths.local.env
pnpm llamacpp:serve
pnpm llamacpp:verify
```

Full guide: [deploy/llamacpp/README.md](../deploy/llamacpp/README.md)

```powershell
# Host API (see backend/.env)
$env:AUDIT_VLLM_BASE_URL="http://127.0.0.1:8081/v1"
$env:AUDIT_VLLM_SERVED_MODEL="nuextract3-q4_k_m"
pnpm dev:all
```

## Kubernetes values

```yaml
config:
  inferenceMode: vllm
  vllmBaseUrl: https://your-vlm-host/v1
  vllmServedModel: numind/NuExtract3

workerExtract:
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
```

Put `AUDIT_VLLM_API_KEY` in `repody-runtime-secrets` when the endpoint requires auth.

## Troubleshooting

| Symptom | Check |
|---------|-------|
| `Repody VLM is unavailable` | Worker pod can reach `$AUDIT_VLLM_BASE_URL/models` |
| 401/403 | `AUDIT_VLLM_API_KEY` exists in the runtime Secret |
| Extraction timeout | Increase `AUDIT_REPODY_VLM_TIMEOUT_SECONDS`; check remote cold start |
| Wrong JSON | Runtime must support NuExtract `chat_template_kwargs` |
| llama-server ignores template | Use `--jinja`; verify with `pnpm llamacpp:verify` |
