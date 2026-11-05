# Document extraction

Repody extracts each workflow document with a vision-language model on an OpenAI-compatible server
(llama-server locally, any OpenAI-compatible endpoint in Kubernetes). Workers call it over HTTP; the
backend image ships no model weights.

| Documents | Model | Code | Official docs | Local server |
|---|---|---|---|---|
| With fields (structured JSON) | NuExtract3 | `extraction/nuextract.py`, `render.py` | [numind/NuExtract3-GGUF](https://huggingface.co/numind/NuExtract3-GGUF) | `pnpm llamacpp:serve` :8081 |
| Without fields (Markdown), default | NuExtract3, markdown mode | `extraction/nuextract.py` | same | same |
| Without fields, `AUDIT_MARKDOWN_PROVIDER=lightonocr` | LightOnOCR-3-4B | `extraction/lightonocr.py` | [lightonai/LightOnOCR-3-4B](https://huggingface.co/lightonai/LightOnOCR-3-4B), [client](https://github.com/lightonai/LightOnOCR) | `pnpm lightonocr:serve` :8082 |

NuExtract's structured JSON is stored as `extraction.rawText`; the leaf rows in `extracted_fields`
are derived for the UI and the rules. Markdown is stored as `extraction.markdownText`.

### What you configure

Only wiring and limits; requests follow the model cards (`extraction/nuextract.py`, `lightonocr.py`).

```env
AUDIT_LLAMACPP_BASE_URL=http://127.0.0.1:8081/v1
AUDIT_LLAMACPP_SERVED_MODEL=nuextract3-q8_0
AUDIT_LLAMACPP_API_KEY=

# Optional: LightOnOCR-3 for Markdown
AUDIT_MARKDOWN_PROVIDER=nuextract          # or lightonocr
AUDIT_LIGHTONOCR_BASE_URL=http://127.0.0.1:8082/v1
AUDIT_LIGHTONOCR_SERVED_MODEL=lightonocr-3-4b

AUDIT_INFERENCE_TIMEOUT_SECONDS=180
AUDIT_MAX_PAGES_PER_DOCUMENT=              # default: every page
```

### Local development

```powershell
winget install llama.cpp   # or brew install llama.cpp on macOS
copy deploy\llamacpp\paths.local.env.example deploy\llamacpp\paths.local.env
pnpm llamacpp:serve
pnpm llamacpp:verify
pnpm lightonocr:serve      # only with AUDIT_MARKDOWN_PROVIDER=lightonocr
```

Guide: [deploy/llamacpp/README.md](../deploy/llamacpp/README.md).

### Kubernetes

Set the endpoints in the chart's `config` (`deploy/helm/repody/values.yaml`):

```yaml
config:
  AUDIT_LLAMACPP_BASE_URL: https://your-inference-host/v1
  AUDIT_LLAMACPP_SERVED_MODEL: nuextract3-q8_0
  AUDIT_MARKDOWN_PROVIDER: nuextract
```

Put `AUDIT_LLAMACPP_API_KEY` (and `AUDIT_LIGHTONOCR_API_KEY`) in the runtime secret when the
endpoint requires auth.

### NuExtract3 requests (model card)

| Input | Behaviour |
|-------|-----------|
| PDF | Every page as PNG at **170 DPI** (the card's PDF example), all pages in one request |
| Image | The uploaded PNG/JPEG/WebP as it is |
| Structured | `chat_template_kwargs`: `template` (`json.dumps(..., indent=4)`), `instructions`, `enable_thinking: false`; temperature **0.2**, or **0** with in-context examples |
| `instructions` | The document's notes, then a `Field guidance:` list built from the field descriptions |
| In-context examples | `developer` messages, input then expected output |
| Markdown | `chat_template_kwargs.mode: "markdown"`, `enable_thinking: false`, temperature **0** |

### LightOnOCR-3 requests (model card and official client)

| Input | Behaviour |
|-------|-----------|
| PDF | Each page rendered at **2048 px** on its longest edge, one request per page |
| Image | Downscaled to 2048 px on its longest edge when larger (never upscaled) |
| Request | The image alone (transcription mode), `enable_thinking: false`, temperature **0.2**, top_p **1.0** |
| Output | The model's Markdown as it comes (the client's optional escaped-math repair is not applied) |

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
