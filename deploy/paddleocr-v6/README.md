# PP-OCRv6 Basic Serving (host)

Official PaddleOCR **Basic Serving** for catalog id `paddleocr:v6`.

Docs:
- [Serving](https://www.paddleocr.ai/latest/en/version3.x/inference_deployment/serving/serving.html)
- [OCR pipeline](https://www.paddleocr.ai/latest/en/version3.x/pipeline_usage/OCR.html)

## Official steps

```powershell
# 1.1 Install serving plugin
pnpm paddleocr:v6:install
# → paddlex --install serving

# 1.2 Run the server
pnpm paddleocr:v6:serve
# → paddlex --serve --pipeline deploy/paddleocr-v6/OCR.yaml --host 0.0.0.0 --port 8868

# 1.3 Invoke POST /ocr
pnpm paddleocr:v6:verify
```

Pipeline config `OCR.yaml` is the official OCR export (`PP-OCRv6_medium_*`) plus:

```yaml
Serving:
  visualize: False
  extra:
    max_num_input_imgs: null
```

## Optional env

| Env | Default | Meaning |
|---|---|---|
| `AUDIT_PADDLEOCR_V6_PORT` | `8868` | `--port` |
| `AUDIT_PADDLEOCR_V6_HOST` | `0.0.0.0` | `--host` |
| `AUDIT_PADDLEOCR_V6_DEVICE` | (auto) | `--device` e.g. `gpu:0` / `cpu` |
| `AUDIT_PADDLEOCR_V6_USE_HPIP` | unset | pass `--use_hpip` (high-performance inference plugin) |

## Client

Platform adapter: `backend/src/repody/extraction/paddleocr_v6.py`  
Mirrors the official Python example: Base64 `file` + `fileType` (`0` PDF / `1` image), plus `visualize: false`.
