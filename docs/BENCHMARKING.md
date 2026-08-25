# Platform benchmarks

Operator benchmarks run from **Settings → Benchmarks** (`/settings?tab=benchmarks`).
They use the same multipart upload and polling contract as the Test tab, measuring
queue, extraction, and validation latency while checking extracted values and rule outcomes.

Reports are written under the operator data path (Compose default
`benchmark-reports/`) as JSON, CSV, and HTML.

## Prerequisites

```powershell
pnpm dev:setup   # first run only
pnpm dev:all
pnpm dev:status
```

Configure external inference (`AUDIT_LLAMACPP_BASE_URL` / `AUDIT_LLAMACPP_SERVED_MODEL`).
For Compose, start host NuExtract first:

```powershell
pnpm llamacpp:serve
pnpm llamacpp:verify
```

Enable operator actions on the API (`AUDIT_OPERATOR_ACTIONS_ENABLED=true`) and, when
using Keycloak, set `AUDIT_OPERATOR_BENCHMARK_USER` (ConfigMap/env) and
`AUDIT_OPERATOR_BENCHMARK_PASSWORD` from the runtime Secret / ESO key (never Helm
`config.*` or ConfigMap) — or use a pre-issued bearer — so the suite can authenticate.

## Phases

- `first` — first observation with extraction cache bypassed
- `warm-N` — warm observation, cache bypassed
- `cache` — repeated run; `cacheHit` must be true

## Custom documents

Upload a PDF plus a manifest (see `e2e/fixtures/documents/Facture.benchmark.json`)
from the Benchmarks tab, or use the built-in Facture fixture when present in the image.

## Production stress test (1000 documents)

End-to-end queue + real document-model extraction at scale. Runs inside the API pod
(same contract as the Test tab: presign → enqueue → poll/SSE queue position → drain).

### Prepare cluster

1. Scale workers and raise admission/rate limits in **client GitOps values**,
   then Helm upgrade / Argo sync and roll out workers:

   ```powershell
   kubectl rollout status deployment/repody-worker-extract -n repody --timeout=300s
   kubectl rollout status deployment/repody-worker-fast -n repody --timeout=300s
   ```

2. Confirm external inference (VLM) is reachable from worker pods (`AUDIT_LLAMACPP_BASE_URL`).

3. Optional OIDC token for auth-enabled stacks:

   ```powershell
   $env:STRESS_BEARER = "<access-token>"
   ```

### Run

```powershell
pnpm stress:prod:smoke    # 20 runs, ~1h timeout cap
pnpm stress:prod          # 1000 runs, strict SLO gates
pnpm stress:prod -- --count 500 --timeout-seconds 7200
```

Reports: `benchmark-reports/prod-stress.json` (also written inside the pod at the same path
when using `kubectl exec`).

### What it covers

| Phase | Checks |
| --- | --- |
| Preflight | `/v1/healthz`, Redis, Taskiq, worker pools, inference, **admission caps** |
| Invalid files | Empty/text/exe uploads, bad presign mime (skipped with `--skip-invalid`) |
| Enqueue | N real `document_model` runs with retry on 429/503 |
| Queue | Samples queue position/depth on polled runs; verifies positions move |
| Drain | Waits until `queuedRuns` + `runningRuns` + `inflightRuns` == 0 (3 idle health polls) |
| SLO | Enqueue target, drain complete, success rate, queue depth observed |

### Throughput tuning

1. **VLM slots** — raise `LLAMACPP_PARALLEL` in `deploy/llamacpp/paths.local.env`, then `pnpm llamacpp:restart`.
2. **Workers** — scale `workerExtract.replicas` / `maxJobs` so the Taskiq extract queue drains.
3. **Healthchecks** — keep `healthzProbeInference: false` so `/v1/healthz` stays fast under load.
4. **OTEL** — set `observability.otelEnabled: false` when no collector is deployed.

### CPU scaling (when GPU/VLM is fixed)

Use CPU HPA and in-process concurrency before adding VLM hardware:

| Profile | File | When |
| --- | --- | --- |
Tune worker replicas / HPA in client GitOps values (see chart defaults in `deploy/helm/repody/values.yaml`).

**What scales on CPU well**

- **API / web** — enqueue, auth, SSE polling (`targetCPUUtilizationPercentage: 70`).
- **worker-fast** — rule validation and logic-only runs (`maxJobs: 8`, HPA max 12).
- **In-pod extract** — PDF render + object-storage fetch (`workerExtract.maxJobs`).

**What does not scale on CPU HPA**

- **worker-extract replicas** while blocked on VLM — average CPU stays low. Keep extract HPA off; scale VLM slots / worker `maxJobs` instead (runs wait in the Taskiq queue).

HPA v2 behavior (scale up in 60s, scale down over 300s) is enabled via `hpaBehavior` in `deploy/helm/repody/values.yaml`. Pods must set `resources.requests.cpu` or HPA cannot compute utilization ([Kubernetes HPA docs](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/)).

Dev-only quick stress (burst 8 + random 20):

```powershell
node scripts/backend-run.mjs --dev python scripts/benchmark_dev_stress.py --api http://127.0.0.1:8000
```

## Document-model compare

The operator **models** profile exercises the registered document-model catalog.
Unavailable models are skipped unless strict mode is set.

| Model | Role | Pass criteria |
| --- | --- | --- |
| `repody:vlm` | Structured field extraction (NuExtract / llama-server) | Field + rule accuracy |
| `repody:vlm:cloud` | Structured extraction via NuExtract Cloud | Field accuracy when cloud key set |
| `paddleocr:v6` | Markdown OCR (PaddleX `POST /ocr`) | Gououiad / fixture OCR score gates |
| `glm:ocr` | Markdown OCR (GLM-OCR llama-server) | Gououiad / fixture OCR score gates |

For Kubernetes runs, point each model's base URL env at the matching external
service before starting a job (`AUDIT_LLAMACPP_*`, `AUDIT_PADDLEOCR_V6_*`,
`AUDIT_GLM_OCR_*`).

## Gououiad CNIE (all extraction paths)

Host benchmark for the Moroccan CNIE recto+verso fixture — scores every registered
document-model path against `e2e/fixtures/documents/gououiad-cnie.ocr-expectations.json`.

```powershell
pnpm dev:all
pnpm benchmark:gououiad
```

Report: `benchmark-reports/gououiad-cnie-full.json`

Paths exercised:

| Path | Mode | Pass gate |
| --- | --- | --- |
| `repody:vlm:markdown` | NuExtract document-to-markdown | core ≥ 40% |
| `repody:vlm:structured` | NuExtract JSON fields (full CNIE schema) | core ≥ 55%, CIN hit |
| `paddleocr:v6` | PP-OCRv6 markdown | core ≥ 40% |
| `glm:ocr` | Official GLM-OCR SDK profile | **LIMIT** on ID cards (image regions skipped) |
| `glm:ocr:id-card` | GLM-OCR + `AUDIT_GLM_OCR_ID_CARD_PROFILE` | core ≥ 40% |

Options: `--only repody:vlm,paddleocr:v6` · `--skip-glm-id-card`
