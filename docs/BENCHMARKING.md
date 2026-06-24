# Platform benchmarks

The benchmark suite runs against the live API in your Kubernetes cluster using the same multipart upload and polling contract as the Test tab. It measures queue, extraction, and validation latency while checking extracted values and rule outcomes.

## Prerequisites

```powershell
pnpm k8s:local:hosts
pnpm k8s:local
pnpm k8s:local:smoke   # optional sanity check
```

Configure external inference before starting if you need real VLM extraction (`REPODY_VLLM_BASE_URL`).

## Run

```powershell
pnpm benchmark quick           # quick Repody VLM baseline
pnpm benchmark models            # all registered document models
pnpm benchmark full              # baseline + full validation cases
pnpm benchmark document-models   # single-document model comparison
```

Reports are written to `benchmark-reports/<timestamp>-<suite-id>/` as JSON, CSV, and HTML.
`latest.json`, `latest.csv`, and `latest.html` point to the newest run.

Benchmarks execute inside the API pod via `kubectl exec`.

## Phases

- `first` — first observation with extraction cache bypassed
- `warm-N` — warm observation, cache bypassed
- `cache` — repeated run; `cacheHit` must be true

For a process-cold measurement, restart OCR workers first:

```powershell
kubectl rollout restart deployment -n repody -l app.kubernetes.io/component=worker-ocr
pnpm benchmark models
```

## Custom documents

Copy `e2e/fixtures/documents/Facture.benchmark.json`, then pass extra args after `--`:

```powershell
pnpm benchmark full -- --document /app/e2e/fixtures/documents/MyDoc.pdf --manifest /app/e2e/fixtures/documents/MyDoc.benchmark.json
```

Useful options:

```text
--warm-runs 3
--minimum-accuracy 0.90
--strict-models
--no-cache-check
--timeout-seconds 1200
--model repody:vlm
```

Unavailable models are skipped by default. Use `--strict-models` to fail on skip.

## OCR compare (Surya OCR 2)

The **Vision models** profile supports multiple engines in parallel (Repody VLM + Surya OCR 2). Select them in **Settings → Benchmarks**.

| Model | Role | Pass criteria |
| --- | --- | --- |
| `repody:vlm` | Structured field extraction | Field + rule accuracy |
| `surya:ocr2` | Layout-aware OCR text (benchmark only) | Non-empty `rawText` + timing |

Surya follows [datalab-to/surya-ocr-2](https://huggingface.co/datalab-to/surya-ocr-2): the worker calls `RecognitionPredictor` with `SuryaInferenceManager` attached to a **pre-running** `llama-server` serving [datalab-to/surya-ocr-2-gguf](https://huggingface.co/datalab-to/surya-ocr-2-gguf). Workers do not auto-spawn inference inside the pod.

On the host:

```powershell
pnpm llamacpp:surya:serve
pnpm llamacpp:surya:verify
```

Rebuild the **worker** image with the optional OCR dependency:

```powershell
docker build --target worker --build-arg BACKEND_EXTRAS=otel,ocr -t repody-worker ./backend
```

Platform env (ConfigMap / `.env`):

```text
AUDIT_SURYA_OCR_ENABLED=true
AUDIT_SURYA_INFERENCE_BACKEND=llamacpp
AUDIT_SURYA_INFERENCE_URL=http://host.docker.internal:8001/v1
AUDIT_SURYA_INFERENCE_PARALLEL=8
```

Set `AUDIT_SURYA_INFERENCE_PARALLEL` to match `--parallel` on `llama-server` (default 8 per upstream docs).

Workers use Surya-documented env (`IMAGE_DPI=96`, etc.) with native/lossless page input — no platform upscale. See Settings → Models and `deploy/llamacpp/README.md#surya-ocr-2`.
