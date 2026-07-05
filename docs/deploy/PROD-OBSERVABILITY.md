# Production observability baseline (bundled + OCR)

Minimum signals, alerts, and connection budgeting for Repody production. Clients own Prometheus/Grafana/Loki; this doc defines **what to watch** and **how settings align**.

See also [OBSERVABILITY.md](./OBSERVABILITY.md) for OTLP and log shipping.

## Timeout alignment (OCR)

These must be set together in Helm `config` (wired to `AUDIT_*` in the app ConfigMap):

| Helm key | Env var | Starting value | Rule |
|----------|---------|----------------|------|
| `workerTaskTimeoutMinutes` | `AUDIT_WORKER_TASK_TIMEOUT_MINUTES` | 3 | Taskiq + `process_run` ceiling (**hard max 3**) |
| `repodyVlmTimeoutSeconds` | `AUDIT_REPODY_VLM_TIMEOUT_SECONDS` | 180 | VLM HTTP client ceiling (≤ worker seconds) |
| `staleRunTimeoutMinutes` | `AUDIT_STALE_RUN_TIMEOUT_MINUTES` | 5 | Maintenance reap for `running` |
| `queuedStaleTimeoutMinutes` | `AUDIT_QUEUED_STALE_TIMEOUT_MINUTES` | 60 | Reap `queued` when no workers active |
| `workerExtract.terminationGracePeriodSeconds` | — | 240 | Must be ≥ worker task timeout (seconds) |

**Rule:** `repodyVlmTimeoutSeconds` ≤ `workerTaskTimeoutMinutes` × 60; `staleRunTimeoutMinutes` ≥ worker timeout + one maintenance interval.

## Connection pool budget (bundled OCR)

Defaults from Helm (`dbPoolSize: 5`, `dbMaxOverflow: 10`, `redisMaxConnections: 20`):

```
Postgres connections (worst case) ≈ (api_replicas + ocr_replicas + fast_replicas) × (dbPoolSize + dbMaxOverflow)
Redis connections ≈ (api_replicas + ocr_replicas + fast_replicas) × redisMaxConnections  # upper bound if each pool maxes out
```

Example: 2 API + 2 OCR + 2 fast → up to 6 × 15 = **90** Postgres connections at peak overflow. Size RDS `max_connections` accordingly.

Tune via Helm:

```yaml
config:
  dbPoolSize: 5
  dbMaxOverflow: 10
  redisMaxConnections: 20
```

## Readiness and health

- **`GET /v1/healthz/live`** — liveness only (always 200 when process up).
- **`GET /v1/healthz`** — readiness: Postgres + **Redis PING**. Returns **503** when Redis is unreachable (`redisOk: false`). Kubernetes should use this for readiness probes.

## Log-based alerts (starting thresholds)

Configure in Loki/Elastic/Datadog from JSON structlog fields:

| Alert | Log / field | Threshold (pilot) |
|-------|-------------|---------------------|
| Run failures | `run_failed`, `run_failed_terminal` | >5% of runs / 15m |
| Stuck runs reaped | `stale_run_reaped` | any in prod (investigate) |
| Dispatch failure | `taskiq_dispatch_failed_terminal`, outbox `status=failed` | any |
| Queue pressure | readiness `queuedRuns` / admission cap | >80% sustained 10m |
| VLM slow | `run_metadata.extractionMs` in completion logs | p99 > 80% of worker timeout |
| Worker unhealthy | pod restart loop on `worker-extract` | >3 restarts / 15m |

## Metrics dashboard (business API)

`GET /v1/metrics` exposes weekly KPIs. Stale-run alert uses `AUDIT_STALE_RUN_TIMEOUT_MINUTES` (aligned with maintenance reap).

**Not included today:** Prometheus `/metrics` scrape endpoint. Use OTLP traces + log alerts until app metrics are added.

## Runbook quick links

| Symptom | Check |
|---------|--------|
| Run stuck `running` | `kubectl logs deploy/repody-worker-extract`; VLM reachability; stale reap logs |
| Run stuck `queued` | Redis; outbox maintenance; admission 503; worker replicas |
| SSE silent | Redis; `redisOk` on healthz; API redis pool |
| 503 on create | Admission caps; scale OCR workers or raise `admissionMaxExtractInflight` |

Platform logs (Kubernetes):

```powershell
kubectl -n repody-app logs -l app.kubernetes.io/component=control --tail=300 --timestamps
kubectl -n repody-app logs -f deploy/repody-worker-extract
```

## Verification scripts

```bash
pnpm prod:readiness -- --api-url https://api.staging.example.com
pnpm ocr:soak -- --api-url https://api.staging.example.com --token $TOKEN --concurrency 8 --duration-minutes 30
```
