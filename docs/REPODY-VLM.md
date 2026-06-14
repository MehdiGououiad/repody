# Repody VLM on vLLM (on-prem & white-label)

**Repody VLM** is the product name in the UI and docs. You do **not** need your own Hugging Face repo — the bundled stack uses the public upstream vision weights (`numind/NuExtract3`) and packages them locally as `agentcontrol/repody-vlm:q4_k_m-16k` for Docker Model Runner.

Repody talks to any **OpenAI-compatible vLLM** endpoint. There is no vendor-specific GPU integration — only `AUDIT_VLLM_BASE_URL` (and an optional API key).

## Platform settings

```env
AUDIT_INFERENCE_MODE=vllm
AUDIT_VLLM_BASE_URL=http://vllm:8000/v1
AUDIT_VLLM_SERVED_MODEL=numind/NuExtract3    # id from vLLM /v1/models (default bundled GPU stack)
AUDIT_VLLM_API_KEY=

AUDIT_REPODY_VLM_TIMEOUT_SECONDS=600
AUDIT_REPODY_VLM_MAX_PAGES_PER_REQUEST=4
AUDIT_REPODY_VLM_WARMUP_ON_START=true
AUDIT_GPU_LIVE_PROBE=true
AUDIT_HEALTHZ_PROBE_INFERENCE=false
```

## Option A — bundled GPU stack (this repo)

```bash
pnpm docker:verify:gpu
pnpm docker:deploy:gpu
```

`compose.gpu.yaml` serves `numind/NuExtract3` with the recommended flags ([upstream vLLM notes](https://huggingface.co/numind/NuExtract3#vllm-deployment)):

- `--limit-mm-per-prompt '{"image": 6, "video": 0}'`
- `--chat-template-content-format openai`
- `--generation-config vllm`
- `--max-model-len 16384`
- MTP speculative decoding (`qwen3_next_mtp`, 2 tokens)

Override with `VLLM_SERVED_MODEL` in `.env` if your vLLM exposes a different id.

## Option B — customer-managed vLLM

```bash
vllm serve numind/NuExtract3 \
  --host 0.0.0.0 --port 8000 \
  --trust-remote-code \
  --limit-mm-per-prompt '{"image": 6, "video": 0}' \
  --chat-template-content-format openai \
  --generation-config vllm \
  --max-model-len 16384
```

Set `AUDIT_VLLM_SERVED_MODEL` to whatever `/v1/models` returns.

Verify:

```bash
curl -s http://YOUR_GPU_HOST:8000/v1/models
curl -s http://YOUR_GPU_HOST:8000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"numind/NuExtract3","messages":[{"role":"user","content":"hi"}],"max_tokens":8}'
```

## Option C — CPU dev (no GPU)

```env
AUDIT_INFERENCE_MODE=docker_model_runner
AUDIT_DOCKER_MODEL_RUNNER_BASE_URL=http://model-runner.docker.internal/engines/llama.cpp/v1
AUDIT_REPODY_VLM_MODEL=agentcontrol/repody-vlm:q4_k_m-16k
```

```bash
pnpm docker:models:pull    # pulls upstream GGUF, tags as agentcontrol/repody-vlm:q4_k_m-16k
pnpm docker:deploy
```

## Troubleshooting

| Symptom | Check |
|---------|--------|
| `Repody VLM is unavailable` | `curl $AUDIT_VLLM_BASE_URL/models`, vLLM logs, firewall |
| Extraction timeout | Raise `AUDIT_REPODY_VLM_TIMEOUT_SECONDS`; GPU finished loading |
| OOM on GPU | Lower `max-model-len` or use a larger GPU |
| Wrong JSON | vLLM needs `openai` chat template + vision limits above |

See [`deploy/repody-vlm.env.example`](../deploy/repody-vlm.env.example).
