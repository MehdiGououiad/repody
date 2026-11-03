# Document extraction (NuExtract)

Repody has one document model, `repody:vlm`: **NuExtract3** served by an OpenAI-compatible
**llama-server**. Workers call the server over HTTP; the backend image ships no model weights.

| Catalog id | Code | Official docs | Local serve |
|---|---|---|---|
| `repody:vlm` | `backend/src/repody/extraction/vlm.py`, `nuextract.py`, `render.py` | [numind/NuExtract3-GGUF](https://huggingface.co/numind/NuExtract3-GGUF) | `pnpm llamacpp:serve` **:8081** |

NuExtract structured JSON is stored verbatim in `run_documents.extraction_meta.rawText`; leaf rows
in `extracted_fields` are derived for the UI and rules. Rules are logic rules only.

Workflows saved before the engine consolidation may still reference `paddleocr:qwen`,
`glm:qwen` or `repody:vlm:cloud`; those ids run on `repody:vlm`.

Repody does not run inference inside the Kubernetes chart. Document extraction calls an external OpenAI-compatible **llama-server** with **NuExtract3**.

Reference: [numind/NuExtract3-GGUF](https://huggingface.co/numind/NuExtract3-GGUF)

### What you configure

Only wiring and operational limits - extraction behavior follows the official NuExtract contract (`extraction/nuextract.py`, `extraction/render.py`).

```env
AUDIT_INFERENCE_MODE=llamacpp
AUDIT_LLAMACPP_BASE_URL=http://127.0.0.1:8081/v1
AUDIT_LLAMACPP_SERVED_MODEL=nuextract3-q4_k_m
AUDIT_LLAMACPP_API_KEY=

AUDIT_REPODY_VLM_TIMEOUT_SECONDS=180
AUDIT_REPODY_VLM_MARKDOWN_ON_EXTRACT=false
AUDIT_HEALTHZ_PROBE_INFERENCE=false
```

| Fixed in code (not configurable) | Value |
|----------------------------------|-------|
| PDF raster | PNG @ **170 DPI** |
| Structured temperature | **0.2** non-thinking · **0.6** thinking · **0** with ICL |
| Markdown temperature | **0** non-thinking · **0.7** thinking |
| Read path | NuExtract vision only |

Thinking mode (`AUDIT_REPODY_VLM_ENABLE_THINKING`, default `false`) and page cap (`AUDIT_REPODY_VLM_MAX_PAGES_PER_REQUEST`, default: all pages) are configurable.

### Local development

```powershell
winget install llama.cpp   # or brew install llama.cpp on macOS
copy deploy\llamacpp\paths.local.env.example deploy\llamacpp\paths.local.env
pnpm llamacpp:serve
pnpm llamacpp:verify
```

Guide: [deploy/llamacpp/README.md](../deploy/llamacpp/README.md). Align `LLAMACPP_MODEL_ALIAS` with `AUDIT_LLAMACPP_SERVED_MODEL`.

### Kubernetes

```yaml
config:
  inferenceMode: llamacpp
  llamacppBaseUrl: https://your-inference-host/v1
  llamacppServedModel: nuextract3-q4_k_m
  repodyVlmTimeoutSeconds: 180

secrets:
  existingSecret: repody-runtime-secrets
```

Put `AUDIT_LLAMACPP_API_KEY` in the runtime secret when the endpoint requires auth.

### NuExtract payload contract

| Input | Behavior |
|-------|----------|
| PDF | PNG @ 170 DPI; **all pages** by default. Optional cap: `AUDIT_REPODY_VLM_MAX_PAGES_PER_REQUEST` |
| Image | Native PNG/JPEG/WebP bytes |
| Other MIME | Rejected - upload PDF or image only |
| Structured call | `chat_template_kwargs.template` (`json.dumps(..., indent=4)`), `instructions`, `enable_thinking`, `temperature=0.2` (or `0.6` thinking; `0` with ICL), no `max_tokens` |
| `instructions` | Workflow document notes + `Field guidance:` list - hints here, not in the template |
| Markdown mode | `chat_template_kwargs.mode: "markdown"`, `temperature=0` (`0.7` when thinking) |
| Source of truth | Model JSON as `extraction.rawText`; leaf `extracted_fields` are UI/rules projection |
| ICL examples | `developer` role pairs from workflow `extractionIclExamples` (text only; local only) |

### Endpoint check

```bash
curl -s "$AUDIT_LLAMACPP_BASE_URL/models"
pnpm llamacpp:verify
```

### Extraction accuracy (NuExtract contract)

Follow the [NuExtract3 guide](https://github.com/numindai/nuextract) - do not hardcode document-specific rules:

| Practice | Why |
|----------|-----|
| Use `verbatim-string` for exact copy | Official type for no reformulation |
| Format/location hints in field **description** | Maps to `instructions` |
| Prefer native image uploads | Avoids extra PDF -> PNG |
| Keep llama.cpp `--image-min-tokens` ≥ 1024 | Qwen-VL accuracy floor |
| Import NuExtract JSON templates in the builder | Same constructors as the docs |
| Prefer one **full name** field on ID photos | Split nom/prenom often swaps on holograms |
| Missing fields are `null` | Official empty result |

### Troubleshooting (NuExtract)

| Symptom | Check |
|---------|-------|
| `Repody VLM is unavailable` | Workers reach `$AUDIT_LLAMACPP_BASE_URL/models` |
| 401/403 | `AUDIT_LLAMACPP_API_KEY` |
| Timeout | Raise `AUDIT_WORKER_TASK_TIMEOUT_MINUTES` and matching `AUDIT_REPODY_VLM_TIMEOUT_SECONDS` (≤ worker×60). Compose extract defaults to 10 min / 600s |
| Wrong JSON | llama-server started with `--jinja` |
| Truncated output | Reduce schema size or set page cap |
| Digits wrong / extra zeros | Prefer Q8_0 (or Q6) GGUF at vision 1024; `verbatim-string` + length/location in description |
