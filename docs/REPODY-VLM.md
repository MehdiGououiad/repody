# External document-model inference

Repody does not run inference inside the Kubernetes chart. Document extraction calls an external OpenAI-compatible **llama-server** endpoint with **NuExtract3**.

Reference: [numind/NuExtract3-GGUF](https://huggingface.co/numind/NuExtract3-GGUF)

Catalog map (all document models): [EXTRACTION.md](./EXTRACTION.md).

## What you configure

Only wiring and operational limits — extraction behavior follows the official NuExtract contract in code (`extraction/nuextract.py`, `extraction/render.py`).

```env
AUDIT_INFERENCE_MODE=llamacpp
AUDIT_LLAMACPP_BASE_URL=http://127.0.0.1:8081/v1
AUDIT_LLAMACPP_SERVED_MODEL=nuextract3-q4_k_m
AUDIT_LLAMACPP_API_KEY=

AUDIT_REPODY_VLM_TIMEOUT_SECONDS=180
# Dual structured+markdown pass (second model call). Markdown-only documents
# still run markdown when enabled on the workflow document.
AUDIT_REPODY_VLM_MARKDOWN_ON_EXTRACT=false
AUDIT_HEALTHZ_PROBE_INFERENCE=false
AUDIT_GPU_LIVE_PROBE=false
```

| Fixed in code (not configurable) | Value |
|----------------------------------|-------|
| PDF raster | PNG @ **170 DPI** |
| Structured temperature | **0.2** non-thinking · **0.6** thinking · **0** with ICL |
| Markdown temperature | **0** non-thinking · **0.7** thinking (official reasoning example) |
| Read path | NuExtract vision only |

Thinking mode (`AUDIT_REPODY_VLM_ENABLE_THINKING`, default `false`) and the page cap
(`AUDIT_REPODY_VLM_MAX_PAGES_PER_REQUEST`, default: send all pages, as in the official
PDF example) are configurable.

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
| PDF | PNG @ 170 DPI; **all pages** by default (official). Optional cap: `AUDIT_REPODY_VLM_MAX_PAGES_PER_REQUEST` |
| Image | Native PNG/JPEG/WebP bytes (no format conversion) |
| Other MIME types | Rejected — upload PDF or image only |
| Structured call | `chat_template_kwargs.template` (`json.dumps(..., indent=4)`), `instructions`, `enable_thinking` from settings, `temperature=0.2` (or `0.6` when thinking; `0` with ICL), no `max_tokens` |
| `instructions` | Workflow document notes, then a `Field guidance:` list of `dotted.path: description` for every described schema field — official NuExtract keeps hints here, not in the template |
| Markdown mode | `chat_template_kwargs.mode: "markdown"`, `temperature=0` (`0.7` when thinking) — one call for markdown-only documents; optional second call after structured when `AUDIT_REPODY_VLM_MARKDOWN_ON_EXTRACT=true` |
| Source of truth | Model JSON stored as `extraction.rawText`; leaf `extracted_fields` are a UI/rules projection only |
| ICL examples | `developer` role pairs from workflow `extractionIclExamples` (text only; local only) |

## Endpoint check

```bash
curl -s "$AUDIT_LLAMACPP_BASE_URL/models"
curl -s "$AUDIT_LLAMACPP_BASE_URL/chat/completions" \
  -H 'Content-Type: application/json' \
  -d '{"model":"nuextract3-q4_k_m","messages":[{"role":"user","content":"hi"}],"max_tokens":8}'
```

Or: `pnpm llamacpp:verify`

## Other document models

Markdown-only **PP-OCRv6** (`paddleocr:v6`) is registered by default over the official PaddleX `POST /ocr` API — see [PADDLEOCR-V6.md](./PADDLEOCR-V6.md).

Markdown-only **GLM-OCR** (`glm:ocr`) via the official SDK (PP-DocLayoutV3) + llama-server on :8083 — see [GLM-OCR.md](./GLM-OCR.md). Started by `pnpm dev:all` (skip with `--no-glmocr`).

## Extraction accuracy (NuExtract contract)

Follow the [NuExtract3 guide](https://github.com/numindai/nuextract) — do not hardcode document-specific rules in the platform:

| Practice | Why |
|----------|-----|
| Use `verbatim-string` for values that must be copied exactly | Official type for no reformulation |
| Put format/location hints in the field **description** (or document instructions) | NuExtract maps these to `instructions` (e.g. “N digits, bottom-right stamp”) |
| Prefer native image uploads when possible | Avoids an extra PDF→PNG step |
| Keep llama.cpp `--image-min-tokens` ≥ 1024 | Qwen-VL accuracy floor; our Arc path caps max at 1024 for VRAM |
| Import NuExtract JSON templates in the builder | Same constructors as the docs: leaf types, `{…}` nests, `["type"]` lists, enums, `[{…}]` rows |
| For personal names on ID photos, prefer one **full name** field | Split `nom`/`prenom` often swaps lines on angled/hologram photos; describe full Latin name explicitly |
| Missing fields are `null` | Official empty result; Repody shows them as not extracted |

Repody only forwards schema types + your descriptions into the official payload shape (`json.dumps(..., indent=4)`, `enable_thinking=false`, structured `temperature=0.2`).

## Troubleshooting

| Symptom | Check |
|---------|-------|
| `Repody VLM is unavailable` | Workers reach `$AUDIT_LLAMACPP_BASE_URL/models` |
| 401/403 | `AUDIT_LLAMACPP_API_KEY` in runtime secret |
| Timeout | Raise `AUDIT_WORKER_TASK_TIMEOUT_MINUTES` (max 15) **and** matching `AUDIT_REPODY_VLM_TIMEOUT_SECONDS` (≤ worker×60). Compose extract defaults to 10 min / 600s. |
| Wrong JSON | llama-server started with `--jinja` |
| Truncated output | Reduce schema size or set `AUDIT_REPODY_VLM_MAX_PAGES_PER_REQUEST` if the server limits multimodal images |
| Digits wrong / extra zeros | Prefer **Q8_0** (or Q6) GGUF at vision 1024; vision 1536+ can crash Arc mid-suite. Use `verbatim-string` + length/location in field description |
