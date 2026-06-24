# llama-server + NuExtract3 for Repody

Serve [numind/NuExtract3-GGUF](https://huggingface.co/numind/NuExtract3-GGUF) with the official
**llama-server** binary (`winget install llama.cpp`). This is Repody’s supported local GGUF runtime;
production reference remains vLLM — see `docs/REPODY-VLM.md`.

## 1. Install llama.cpp

```powershell
winget install llama.cpp
```

Confirm your GPU backend:

```powershell
llama-server --list-devices
```

Use the device id in `paths.local.env` (e.g. `Vulkan0`, `CUDA0`).

## 2. Download the model

| File | Purpose |
|------|---------|
| `NuExtract3-Q8_0.gguf` | Text weights (~4.5 GB) — NuExtract recommended quality |
| `mmproj-NuExtract3-BF16.gguf` | Vision projector (required for images) |

## 3. Configure paths

```powershell
copy deploy\llamacpp\paths.local.env.example deploy\llamacpp\paths.local.env
```

## 4. Start the server

```powershell
pnpm llamacpp:serve
pnpm llamacpp:verify
```

### Load settings (NuExtract + Repody defaults)

Aligned with NuExtract’s low-memory vLLM profile and official non-thinking mode:

| Setting | Value |
|---------|-------|
| Quantization | **Q8_0** weights + BF16 mmproj |
| Context | **16384** |
| Flash attention | on (`-fa on`) |
| KV cache | **q8_0** for K and V |
| Physical batch | **256** (`-ub 256`) |
| GPU offload | all layers (`-ngl 99`) + `--mmproj-offload` |
| Server reasoning | off (`-rea off`) — Repody sends `enable_thinking` per request |
| Chat template | `--jinja` (required for `chat_template_kwargs`) |

API: `http://127.0.0.1:8000/v1` (model id `nuextract3-q8_0`).

## 5. Point Repody at llama-server

```powershell
$env:REPODY_VLLM_BASE_URL="http://host.docker.internal:8000/v1"
$env:REPODY_VLLM_SERVED_MODEL="nuextract3-q8_0"
pnpm k8s:local
kubectl rollout restart deployment -n repody -l app.kubernetes.io/component=worker-ocr
```

See `deploy/llamacpp/repody-llamacpp.env.example`.

## Manual command

```powershell
llama-server `
  -m C:\path\to\NuExtract3-Q8_0.gguf `
  --mmproj C:\path\to\mmproj-NuExtract3-BF16.gguf `
  --host 0.0.0.0 --port 8000 `
  -c 16384 -fa on -ctk q8_0 -ctv q8_0 `
  -ngl 99 --device Vulkan0 --mmproj-offload `
  -ub 256 -a nuextract3-q8_0 --jinja -rea off
```

## Port note

Port **8000** matches the vLLM reference. Avoid **5001** when `pnpm k8s:local` is running
(local registry). `pnpm dev:api` also uses host port 8000 — do not run both.

## Smoke test

```powershell
python deploy/scripts/test-inference-endpoint.py --host http://127.0.0.1:8000
```

## Surya OCR 2

Serve [datalab-to/surya-ocr-2-gguf](https://huggingface.co/datalab-to/surya-ocr-2-gguf) on a **second** `llama-server` port for benchmark OCR compare. Follows [datalab-to/surya-ocr-2](https://huggingface.co/datalab-to/surya-ocr-2): `RecognitionPredictor` + `SuryaInferenceManager` with `SURYA_INFERENCE_BACKEND=llamacpp` and `SURYA_INFERENCE_URL`.

| File | Purpose |
|------|---------|
| `surya-2.gguf` | Surya 2 weights (~1.2 GB) |
| `surya-2-mmproj.gguf` | Vision projector (required) |

```powershell
copy deploy\llamacpp\surya-paths.local.env.example deploy\llamacpp\surya-paths.local.env
pnpm llamacpp:surya:serve
pnpm llamacpp:surya:verify
```

Default API: `http://127.0.0.1:8001/v1` with `--parallel 8` (match `AUDIT_SURYA_INFERENCE_PARALLEL=8`).

Repody workers pass pages as **lossless PNG** (PDF) or **native upload bytes** (images). Surya env follows [datalab-to/surya-ocr-2](https://huggingface.co/datalab-to/surya-ocr-2) — no platform upscale/downscale.

| Setting | Default | Source |
| --- | --- | --- |
| `SURYA_MAX_TOKENS_FULL_PAGE` | 12288 | [datalab-to/surya settings.py](https://github.com/datalab-to/surya/blob/master/surya/settings.py) |
| `IMAGE_DPI` | 96 | datalab-to/surya settings.py |
| `IMAGE_DPI_HIGHRES` | 192 | datalab-to/surya settings.py |
| `DETECTOR_TEXT_THRESHOLD` | 0.6 | datalab-to/surya settings.py |
| `AUDIT_SURYA_LAYOUT_BLOCK_OCR_ENABLED` | false | LayoutPredictor + block OCR (off = full-page) |
| `AUDIT_SURYA_TABLE_RECOGNITION_ENABLED` | false | TableRecPredictor.predict_full per page |
| `AUDIT_SURYA_INFERENCE_PARALLEL` | 8 | Match llama-server `--parallel` |
| `llama-server --ctx-size` | max(16384, parallel × 12288) | datalab-to/surya llamacpp spawn |

Point workers at the host server — see `deploy/llamacpp/repody-surya-llamacpp.env.example` or `values-local.yaml` `suryaInferenceUrl`.

Manual command (matches datalab-to/surya llamacpp spawn):

```powershell
llama-server `
  -m C:\path\to\surya-2.gguf `
  --mmproj C:\path\to\surya-2-mmproj.gguf `
  --host 0.0.0.0 --port 8001 `
  -ngl 99 --device Vulkan0 `
  --parallel 8 --ctx-size 98304 `
  --alias datalab-to/surya-ocr-2 --jinja
```

(`98304` = max(16384, 8 × 12288) with default parallel and per-slot ctx.)
