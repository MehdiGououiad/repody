# Platform benchmarks

The benchmark suite runs against the live API using the same multipart upload and polling contract as the Test tab. It measures queue, extraction, and validation latency while checking extracted values and rule outcomes.

## Prerequisites

For daily local development, start Compose plus the API/UI:

```powershell
pnpm dev:setup   # first run only
pnpm dev:all
pnpm dev:status
```

For OpenShift CRC benchmarks, use `pnpm openshift:client-test` then set
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
kubectl rollout restart deployment -n repody -l app.kubernetes.io/component=worker-extract
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

## Production stress test (1000 documents)

End-to-end queue + real document-model extraction at scale. Runs inside the API pod
(same contract as the Test tab: presign → enqueue → poll/SSE queue position → drain).

### Prepare cluster

1. Scale workers and raise admission/rate limits — merge
   `deploy/client/lab/values.stress-test.crc.yaml` (CRC/single-node) or
   `deploy/client/lab/values.stress-test.yaml` (multi-node) into your promoted values (or append as an
   extra Helm `-f`), then sync Argo / roll out workers:

   ```powershell
   # After editing values.openshift-local.promoted.yaml to include stress-test keys:
   node deploy/scripts/openshift-client-test.mjs register sync
   kubectl rollout status deployment/repody-worker-extract -n repody --timeout=300s
   kubectl rollout status deployment/repody-worker-fast -n repody --timeout=300s
   ```

2. Confirm external inference (VLM) is reachable from worker pods (`AUDIT_VLLM_BASE_URL`).

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
2. **Admission** — set `config.admissionMaxExtractInflight` to match parallel slots (see `values.stress-test.crc.yaml` for CRC).
3. **Workers** — scale `workerExtract.replicas` on hardware with ≥2 GiB RAM per pod (CRC: stay at 1).
4. **Healthchecks** — keep `healthzProbeInference: false` so `/v1/healthz` stays fast under load.
5. **OTEL** — disable on CRC lab (`observability.otelEnabled: false`) when no collector is deployed.

### CPU scaling (when GPU/VLM is fixed)

Use CPU HPA and in-process concurrency before adding VLM hardware:

| Profile | File | When |
| --- | --- | --- |
| Multi-node HPA | `deploy/client/lab/values.cpu-scale.yaml` | metrics-server or OpenShift monitoring installed |
| CRC manual | `deploy/client/lab/values.cpu-scale.crc.yaml` | single-node lab; fixed replicas + CPU limits |

**What scales on CPU well**

- **API / web** — enqueue, auth, SSE polling (`targetCPUUtilizationPercentage: 70`).
- **worker-fast** — rule validation and logic-only runs (`maxJobs: 8`, HPA max 12).
- **In-pod extract** — PDF render + MinIO fetch (`parallelStorageFetch`, `parallelDocExtraction`, `workerExtract.maxJobs`).

**What does not scale on CPU HPA**

- **worker-extract replicas** while blocked on VLM — average CPU stays low. Keep extract HPA off; scale VLM slots and `admissionMaxExtractInflight` instead.

HPA v2 behavior (scale up in 60s, scale down over 300s) is enabled via `hpaBehavior` in `deploy/helm/repody/values.yaml`. Pods must set `resources.requests.cpu` or HPA cannot compute utilization ([Kubernetes HPA docs](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/)).

CRC lab: `kubectl top` fails without metrics-server — merge `values.cpu-scale.crc.yaml` for manual replica/CPU tuning. On a ~12 GiB CRC node, keep memory **requests** low and raise **CPU limits** plus in-process `maxJobs` (avoid second extract pod during rollout):

```powershell
kubectl -n repody patch configmap repody-config --patch-file deploy/client/lab/stress-configmap-patch.json
kubectl -n repody set env deployment/repody-worker-fast AUDIT_WORKER_FAST_MAX_JOBS=4
kubectl -n repody rollout restart deployment/repody-worker-fast deployment/repody-worker-extract
```

CRC lab enables one extract + one fast worker by default (`values.openshift-local.crc.yaml`).
Use the stress overlay before a 1000-run test.

Dev-only quick stress (burst 8 + random 20):

```powershell
node scripts/backend-run.mjs --dev python scripts/benchmark_dev.py stress --api http://127.0.0.1:8000
```

## Document-model compare

The **models** profile exercises the registered document-model catalog. Repody VLM is the
supported document model today; unavailable models are skipped unless `--strict-models`
is set.

| Model | Role | Pass criteria |
| --- | --- | --- |
| `repody:vlm` | Structured field extraction | Field + rule accuracy |

For Kubernetes benchmarks, point `AUDIT_VLLM_BASE_URL` and `AUDIT_VLLM_SERVED_MODEL`
at the external vLLM or llama-server endpoint before running the suite.
