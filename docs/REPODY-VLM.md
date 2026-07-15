# External document-model inference

Repody does not run inference inside the Kubernetes chart. Document extraction calls an external OpenAI-compatible **llama-server** endpoint with **NuExtract3**.

Reference: [numind/NuExtract3-GGUF](https://huggingface.co/numind/NuExtract3-GGUF)

## What you configure

Only wiring and operational limits — extraction behavior follows the official NuExtract contract in code (`nuextract_contract.py`).

```env
AUDIT_INFERENCE_MODE=llamacpp
AUDIT_LLAMACPP_BASE_URL=http://127.0.0.1:8081/v1
AUDIT_LLAMACPP_SERVED_MODEL=nuextract3-q4_k_m
AUDIT_LLAMACPP_API_KEY=

AUDIT_REPODY_VLM_TIMEOUT_SECONDS=180
AUDIT_REPODY_VLM_MARKDOWN_ON_EXTRACT=true
AUDIT_HEALTHZ_PROBE_INFERENCE=false
AUDIT_GPU_LIVE_PROBE=false
```

| Fixed in code (not configurable) | Value |
|----------------------------------|-------|
| PDF raster | PNG @ **170 DPI** |
| Thinking mode | `enable_thinking=false`, `temperature=0.2` |
| Max pages per request | **6** |
| Read path | NuExtract vision only |

## Local development

```powershell
winget install llama.cpp
copy deploy\llamacpp\paths.local.env.example deploy\llamacpp\paths.local.env
pnpm llamacpp:serve
pnpm llamacpp:verify
pnpm dev:all
```

Guide: [deploy/llamacpp/README.md](../deploy/llamacpp/README.md) · Commands: [docs/COMMANDS.md](./COMMANDS.md)

Align `LLAMACPP_MODEL_ALIAS` in `deploy/llamacpp/paths.local.env` with `AUDIT_LLAMACPP_SERVED_MODEL`.

## Kubernetes

```yaml
config:
  inferenceMode: llamacpp
  llamacppBaseUrl: https://your-inference-host/v1
  # Must match llama-server /v1/models id (official local: NuExtract3-Q4_K_M → nuextract3-q4_k_m).
  llamacppServedModel: nuextract3-q4_k_m
  repodyVlmTimeoutSeconds: 180

secrets:
  existingSecret: repody-runtime-secrets
```

Put `AUDIT_LLAMACPP_API_KEY` in the runtime secret when the endpoint requires auth.

## NuExtract payload contract

Structured extraction follows the [NuExtract3-GGUF](https://huggingface.co/numind/NuExtract3-GGUF) examples:

| Input | Behavior |
|-------|----------|
| PDF | PNG @ 170 DPI, up to 6 pages per request |
| Image | Native bytes (PNG, JPEG, WebP) |
| Other MIME types | Rejected — upload PDF or image only |
| Structured call | `chat_template_kwargs.template`, optional `instructions`, `enable_thinking=false`, `temperature=0.2`, no `max_tokens` |
| Markdown mode | `chat_template_kwargs.mode: "markdown"` when the document has no schema fields |
| ICL examples | `developer` role pairs from workflow `extractionIclExamples` (text only) |

## Endpoint check

```bash
curl -s "$AUDIT_LLAMACPP_BASE_URL/models"
curl -s "$AUDIT_LLAMACPP_BASE_URL/chat/completions" \
  -H 'Content-Type: application/json' \
  -d '{"model":"nuextract3-q4_k_m","messages":[{"role":"user","content":"hi"}],"max_tokens":8}'
```

Or: `pnpm llamacpp:verify`

## Troubleshooting

| Symptom | Check |
|---------|-------|
| `Repody VLM is unavailable` | Workers reach `$AUDIT_LLAMACPP_BASE_URL/models` |
| 401/403 | `AUDIT_LLAMACPP_API_KEY` in runtime secret |
| Timeout | Increase `AUDIT_REPODY_VLM_TIMEOUT_SECONDS`; check inference cold start |
| Wrong JSON | llama-server started with `--jinja` |
| Truncated output | Reduce schema size or page count (max 6 pages per request) |
