# PP-OCRv6 (markdown-only) — official Basic Serving

Catalog id: `paddleocr:v6`. Document → text/Markdown via the official PaddleX **Basic Serving** API (`POST /ocr`). Structured field extraction stays on **Repody VLM** (`repody:vlm` / NuExtract) or **`paddleocr:qwen`**.

Follows:
- [Serving](https://www.paddleocr.ai/latest/en/version3.x/inference_deployment/serving/serving.html)
- [OCR pipeline](https://www.paddleocr.ai/latest/en/version3.x/pipeline_usage/OCR.html)

Catalog map (all document models): [EXTRACTION.md](./EXTRACTION.md).

Enabled by default (`AUDIT_PADDLEOCR_V6_ENABLED=true`). Started automatically by `pnpm platform`.

## Official flow

### 1.1 Install + run (automatic)

Prefer the main CLIs — **no separate install step**:

```powershell
pnpm platform
```

`paddleocr-v6-serve` **auto-installs** the official stack into `backend/.venv` on first
serve if deps are missing (same packages as the docs):

1. [PaddlePaddle 3.2.0 CPU](https://www.paddleocr.ai/latest/en/version3.x/paddlepaddle_installation.html)
2. [`paddleocr`](https://www.paddleocr.ai/latest/en/version3.x/installation.html) (pulls `paddlex`)
3. `paddlex[serving]` — the full serving extra

Docs: [Serving](https://www.paddleocr.ai/latest/en/version3.x/inference_deployment/serving/serving.html)

Advanced / CI only: `node deploy/scripts/paddleocr-v6-serve.mjs install`  
Skip auto-install: `REPODY_PADDLEOCR_SKIP_INSTALL=1`

### 1.2 Run the server alone (advanced)

```powershell
pnpm paddleocr:v6:serve
# auto-installs if needed, then:
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
| `AUDIT_PADDLEOCR_V6_USE_HPIP=true` | `--use_hpip` — also installs the `hpi-cpu` + `paddle2onnx` plugins |
| `AUDIT_PADDLEOCR_V6_HPI_CONFIG='{"backend":"onnxruntime"}'` | `--hpi_config` |
| `AUDIT_PADDLEOCR_V6_USE_DOC_ORIENTATION_CLASSIFY=false` | Official `/ocr` override; skip orientation classification |
| `AUDIT_PADDLEOCR_V6_USE_DOC_UNWARPING=false` | Official `/ocr` override; skip document unwarping |
| `AUDIT_PADDLEOCR_V6_USE_TEXTLINE_ORIENTATION=false` | Official `/ocr` override; skip text-line orientation |

High-performance inference is **Linux x86-64 only** upstream. On other platforms the
serve script logs a warning and drops `--use_hpip` rather than passing a flag the
plugin cannot honour.

### 1.3 Invoke the service

```powershell
pnpm paddleocr:v6:verify
```

Client body (same as official Python example + `visualize: false`):

```json
{
  "file": "<base64>",
  "fileType": 1,
  "visualize": false,
  "useDocOrientationClassify": true,
  "useDocUnwarping": true,
  "useTextlineOrientation": true
}
```

- `fileType`: `0` = PDF, `1` = image  
- Response: `result.ocrResults[].prunedResult.rec_texts`

`verify` issues that exact request against a 1×1 PNG and requires `errorCode: 0` plus a
`result.ocrResults` array, so it checks the documented contract rather than mere
reachability. Readiness polling during startup uses an empty body, which the official
schema must reject with a 4xx (`file` is required); a 5xx or 404 is treated as not ready.

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
AUDIT_PADDLEOCR_V6_USE_DOC_ORIENTATION_CLASSIFY=true
AUDIT_PADDLEOCR_V6_USE_DOC_UNWARPING=true
AUDIT_PADDLEOCR_V6_USE_TEXTLINE_ORIENTATION=true
```

Extract workers use `http://host.docker.internal:8868`.

## Day-to-day

```powershell
pnpm platform                # Hub + PP-OCR + Qwen
pnpm paddleocr:v6:serve      # OCR alone (advanced; auto-installs)
pnpm paddleocr:v6:verify
pnpm paddleocr:v6:warmup
pnpm paddleocr:v6:stop
```

Skip OCR: `pnpm platform -- --no-paddle`

## Adapter

- Config: `deploy/paddleocr-v6/OCR.yaml`
- Serve: `deploy/scripts/paddleocr-v6-serve.mjs`
- Client: `backend/src/repody/extraction/paddleocr_v6.py`
- Unit tests: `backend/tests/unit/extraction/test_paddleocr_v6.py`
- Live Gououiad: `backend/tests/live/platform/test_paddleocr_gououiad_markdown.py` (`PADDLEOCR_GOUOUIAD_LIVE=1`)

## Related

- [deploy/paddleocr-v6/README.md](../deploy/paddleocr-v6/README.md)
- [REPODY-VLM.md](./REPODY-VLM.md) — structured NuExtract / llama.cpp
- [GLM-OCR.md](./GLM-OCR.md) — GLM-OCR markdown OCR
- [COMMANDS.md](./COMMANDS.md)
