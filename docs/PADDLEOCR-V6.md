# PP-OCRv6 (markdown-only) — official Basic Serving

Catalog id: `paddleocr:v6`. Document → text/Markdown via the official PaddleX **Basic Serving** API (`POST /ocr`). Structured field extraction stays on **Repody VLM** (`repody:vlm` / NuExtract).

Follows:
- [Serving](https://www.paddleocr.ai/latest/en/version3.x/inference_deployment/serving/serving.html)
- [OCR pipeline](https://www.paddleocr.ai/latest/en/version3.x/pipeline_usage/OCR.html)

Catalog map (all document models): [EXTRACTION.md](./EXTRACTION.md).

Enabled by default (`AUDIT_PADDLEOCR_V6_ENABLED=true`). Started automatically by `pnpm dev:all` (and `pnpm dev`).

## Official flow

### 1.1 Install serving plugin

```powershell
pnpm paddleocr:v6:install
# paddlex --install serving
```

### 1.2 Run the server

```powershell
pnpm paddleocr:v6:serve
# paddlex --serve --pipeline deploy/paddleocr-v6/OCR.yaml --host 0.0.0.0 --port 8868
```

Pipeline config uses default **PP-OCRv6_medium** det/rec models, with:

```yaml
Serving:
  visualize: False
  extra:
    max_num_input_imgs: null   # no 10-page PDF cap
```

Optional:

| Env | Effect |
|---|---|
| `AUDIT_PADDLEOCR_V6_DEVICE=gpu:0` | `--device` |
| `AUDIT_PADDLEOCR_V6_USE_HPIP=true` | `--use_hpip` (high-performance inference on the same service) |

### 1.3 Invoke the service

```powershell
pnpm paddleocr:v6:verify
```

Client body (same as official Python example + `visualize: false`):

```json
{ "file": "<base64>", "fileType": 1, "visualize": false }
```

- `fileType`: `0` = PDF, `1` = image  
- Response: `result.ocrResults[].prunedResult.rec_texts`

### Accuracy notes (official defaults kept)

- `use_doc_preprocessor` / textline orientation stay **on** (orientation + unwarp help scans).
- `visualize: false` only skips drawing boxes in the response — it does **not** change recognition.
- Det/rec: **PP-OCRv6_medium** (pipeline default family for v6).
- Client sends the raw file (no platform downscale) so serving keeps full resolution.

## Env

```env
AUDIT_PADDLEOCR_V6_ENABLED=true
AUDIT_PADDLEOCR_V6_BASE_URL=http://127.0.0.1:8868
AUDIT_PADDLEOCR_V6_TIMEOUT_SECONDS=180
```

Extract workers use `http://host.docker.internal:8868`.

## Day-to-day

```powershell
pnpm dev:all                 # NuExtract + PP-OCRv6 + GLM-OCR + observability + API/UI
pnpm paddleocr:v6:serve      # OCR alone (background)
pnpm paddleocr:v6:verify
pnpm paddleocr:v6:warmup
pnpm paddleocr:v6:stop
```

Skip OCR: `pnpm dev:all -- --no-paddleocr`

## Adapter

- Config: `deploy/paddleocr-v6/OCR.yaml`
- Serve: `deploy/scripts/paddleocr-v6-serve.mjs`
- Client: `backend/src/audit_workbench/extraction/paddleocr_v6.py`
- Unit tests: `backend/tests/unit/extraction/test_paddleocr_v6.py`
- Live Gououiad: `backend/tests/live/platform/test_paddleocr_gououiad_markdown.py` (`PADDLEOCR_GOUOUIAD_LIVE=1`)

## Related

- [deploy/paddleocr-v6/README.md](../deploy/paddleocr-v6/README.md)
- [REPODY-VLM.md](./REPODY-VLM.md) — structured NuExtract / llama.cpp
- [GLM-OCR.md](./GLM-OCR.md) — GLM-OCR markdown OCR
- [COMMANDS.md](./COMMANDS.md)
