# Document extraction

Repody extracts every workflow document with **NuExtract3** on an OpenAI-compatible server: vLLM with
the full model in production ([deploy/modal/README.md](../deploy/modal/README.md)), or llama-server
with a GGUF locally. Workers call it over HTTP, and the backend image ships no model weights.

| Documents | Mode | Code | Official docs |
|---|---|---|---|
| With fields | Structured JSON | `extraction/nuextract.py`, `render.py` | [numind/NuExtract3](https://huggingface.co/numind/NuExtract3) (vLLM); [GGUF](https://huggingface.co/numind/NuExtract3-GGUF) for llama-server |
| Without fields | Markdown | `extraction/nuextract.py` | same |

NuExtract's structured JSON is stored as `extraction.rawText`; the leaf rows in `extracted_fields`
are derived for the UI and the rules. Markdown is stored as `extraction.markdownText`.

### What you configure

Only wiring and limits; requests follow the model card (`extraction/nuextract.py`).

```env
AUDIT_LLAMACPP_BASE_URL=http://127.0.0.1:8081/v1
AUDIT_LLAMACPP_SERVED_MODEL=nuextract3-q8_0
AUDIT_LLAMACPP_API_KEY=

AUDIT_INFERENCE_TIMEOUT_SECONDS=180
AUDIT_MAX_PAGES_PER_DOCUMENT=              # default: every page
```

### Local development

```powershell
winget install llama.cpp
copy deploy\llamacpp\paths.local.env.example deploy\llamacpp\paths.local.env
pnpm llamacpp:serve
pnpm llamacpp:verify
```

Guide: [deploy/llamacpp/README.md](../deploy/llamacpp/README.md).

### Kubernetes

Set the endpoints in the chart's `config` (`deploy/helm/repody/values.yaml`):

```yaml
config:
  AUDIT_LLAMACPP_BASE_URL: https://your-inference-host/v1
  AUDIT_LLAMACPP_SERVED_MODEL: nuextract3-q8_0
```

Put `AUDIT_LLAMACPP_API_KEY` in the runtime secret when the endpoint requires auth.

### NuExtract3 requests ([model card](https://huggingface.co/numind/NuExtract3), vLLM examples)

| Input | Behaviour |
|-------|-----------|
| PDF | Every page as PNG at **170 DPI** (the card's PDF example), all pages in one request |
| Image | The uploaded PNG/JPEG/WebP, turned upright by its EXIF orientation and sent as PNG (the same pixels) |
| Structured | `chat_template_kwargs`: `template` (`json.dumps(..., indent=4)`), `instructions`, `enable_thinking: false`; temperature **0.2** (the card's non-thinking mode), with or without in-context examples |
| `instructions` | The document's notes, then a `Field guidance:` list built from the field descriptions |
| In-context examples | `developer` messages, input then expected output |
| Markdown | `chat_template_kwargs.mode: "markdown"`, `enable_thinking: false`, temperature **1** (the card's document-to-Markdown example) |

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
| Import NuExtract JSON templates in the builder | Same constructors as the docs |
| Prefer one **full name** field on ID photos | Split nom/prenom often swaps on holograms |
| Missing fields are `null` | Official empty result |

### Troubleshooting (NuExtract)

| Symptom | Check |
|---------|-------|
| `Repody VLM is unavailable` | Workers reach `$AUDIT_LLAMACPP_BASE_URL/models` |
| 401/403 | `AUDIT_LLAMACPP_API_KEY` |
| Timeout | Raise `AUDIT_RUN_TIMEOUT_MINUTES` and `AUDIT_INFERENCE_TIMEOUT_SECONDS` (≤ run timeout). Compose extract defaults to 10 min / 600s |
| Wrong JSON | llama-server started with `--jinja` |
| Truncated output | Reduce schema size or set page cap |
| Digits wrong / extra zeros | Prefer the Q8_0 GGUF; `verbatim-string` + length/location in description |
