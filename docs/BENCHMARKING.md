# Platform benchmarks

The benchmark suite runs through the live Docker API using the same multipart upload
and polling contract as the Test tab. It measures queue, extraction, and validation
latency while checking extracted values and rule outcomes.

## Start the platform

```powershell
pnpm dev:nowarmup
```

Use `pnpm dev:warmup` when you want Repody VLM warmed on worker start.

## Run

Quick Repody VLM baseline:

```powershell
pnpm benchmark:quick
```

All registered document models:

```powershell
pnpm benchmark:models
```

Baseline plus full validation cases:

```powershell
pnpm benchmark:suite
```

Reports are written to `benchmark-reports/<timestamp>-<suite-id>/` as JSON, CSV, and HTML.
`latest.json`, `latest.csv`, and `latest.html` point to the newest run.

## Phases

- `first` — first observation with extraction cache bypassed
- `warm-N` — warm observation, cache bypassed
- `cache` — repeated run; `cacheHit` must be true

For a process-cold measurement, restart workers first:

```powershell
pnpm docker:restart:workers
pnpm benchmark:models
```

## Custom documents

Copy `e2e/fixtures/documents/Facture.benchmark.json`, then:

```powershell
pnpm benchmark:suite -- --document /app/e2e/fixtures/documents/MyDoc.pdf --manifest /app/e2e/fixtures/documents/MyDoc.benchmark.json
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
