# Platform benchmarks

The benchmark suite runs against the live API using the same multipart upload and polling contract as the Test tab. It measures queue, extraction, and validation latency while checking extracted values and rule outcomes.

## Prerequisites

For daily local development, start Compose plus the API/UI:

```powershell
pnpm dev:setup   # first run only
pnpm dev:all
pnpm dev:status
```

For OpenShift CRC benchmarks, use `pnpm openshift:promote` then set
`REPODY_K8S_NAMESPACE=repody` and `REPODY_API_DEPLOY=deploy/repody-api` if not using defaults.

Configure external inference before cluster benchmarks (`AUDIT_VLLM_BASE_URL` /
`AUDIT_VLLM_SERVED_MODEL`). For Compose, start host NuExtract first:

```powershell
pnpm llamacpp:serve
pnpm llamacpp:verify
```

## Run

```powershell
pnpm benchmark quick           # quick Repody VLM baseline
pnpm benchmark models            # all registered document models
pnpm benchmark full              # baseline + full validation cases
pnpm benchmark document-models   # direct in-pod document-model adapter benchmark
```

Reports are written to `benchmark-reports/<timestamp>-<suite-id>/` as JSON, CSV, and HTML.
`latest.json`, `latest.csv`, and `latest.html` point to the newest run.

`pnpm benchmark` executes inside the API pod via `kubectl exec`. For local Compose,
use the operator benchmark UI at `/settings?tab=benchmarks` or run the backend script
directly with `pnpm test:platform:integration`/API flags when the local API is up.

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

## Document-model compare

The **models** profile exercises the registered document-model catalog. Repody VLM is the
supported document model today; unavailable models are skipped unless `--strict-models`
is set.

| Model | Role | Pass criteria |
| --- | --- | --- |
| `repody:vlm` | Structured field extraction | Field + rule accuracy |

For Kubernetes benchmarks, point `AUDIT_VLLM_BASE_URL` and `AUDIT_VLLM_SERVED_MODEL`
at the external vLLM or llama-server endpoint before running the suite.
