# Platform logs (Loki + Grafana + Tempo)

Self-hosted log aggregation and distributed tracing for Docker services (api, worker, worker-fast, web, vllm).

For **browser and client-side errors** (events that never hit the API), see [GLITCHTIP.md](./GLITCHTIP.md).

| Signal | Tool |
|--------|------|
| Full platform log stream (workers, api, `run_id`) | **Loki** (this doc) |
| Exceptions + API warning/error lines | **GlitchTip** |
| Distributed traces (optional) | **Tempo** (`deploy:obs`) |

## Start stack with logging + tracing

```powershell
pnpm docker:up:obs
```

Or production with logs and OTLP traces:

```powershell
pnpm docker:deploy:obs
```

`compose.observability.yaml` — **Loki + Promtail + Grafana** (`--profile obs`).  
`compose.observability-traces.yaml` — **Tempo + OTEL** on api/workers (`--profile obs-traces`).  
`pnpm docker:deploy:obs` merges both.

### Dev stack flags

```powershell
pnpm dev:warmup                  # no Grafana/Tempo
pnpm dev:warmup -- --logs        # Grafana/Loki only
pnpm dev:warmup -- --traces      # Grafana/Loki + Tempo/OTEL
```

Same flags work with `pnpm dev:nowarmup`.

Observability only (if the app is already running):

```powershell
pnpm docker:obs
```

## Structured JSON logs

API and workers call the same `configure_logging()` path. In production (`AUDIT_LOG_JSON=true`), logs are JSON with fields such as:

| Field | Example | Role |
|-------|---------|------|
| `event` / `body` | `repody_vlm_done` | Repody VLM extraction finished (legacy log key) |
| `level` | `info` | Log level |
| `run_id` | `run_abc` | Audit run (worker) |
| `workflow_id` | `wf_123` | Workflow |
| `request_id` | UUID | HTTP correlation id (API → Hatchet → worker) |
| `trace_id` | hex | OpenTelemetry trace (when OTEL enabled) |
| `service.name` | `audit-workbench-worker-ocr` | Process |

Promtail parses JSON lines into Loki **structured metadata** (not high-cardinality labels). Sensitive keys (`token`, `password`, etc.) are redacted in the application before emit.

## Grafana UI

| | |
|--|--|
| URL | http://localhost:3001 |
| User | `admin` |
| Password | `audit` |

1. Open **Explore** (compass icon).
2. Datasource **Loki** (default).
3. Example queries:

```logql
{service="worker"}
```

```logql
{service="worker"} | json | event="repody_vlm_done"
```

```logql
{service="api"} | json | event_domain="admission"
```

```logql
{service=~"api|worker.*"} | json | level="error"
```

Pre-built dashboard: **Dashboards → Repody → Platform logs** (errors, document model, admission, HTTP 5xx panels).

**Traces:** Grafana → Explore → datasource **Tempo**. Link from a trace to Loki logs via `trace_id`.

## Labels

| Label | Example | Meaning |
|-------|---------|---------|
| `service` | `worker`, `api`, `vllm` | Compose service name |
| `container` | `agentcontrol-worker-1` | Container name |
| `stream` | `stdout` / `stderr` | Log stream |

Only containers from the Compose project **`agentcontrol`** are collected (your folder name). If you use another project name, edit `observability/promtail-config.yaml` regex.

## Cursor / CLI

Grafana is the main UI. For the agent or terminal:

```powershell
# Live tail (no Grafana)
pnpm docker:logs:platform

# Loki ready check
curl.exe http://localhost:3100/ready
```

To query Loki from a script (optional):

```powershell
curl.exe -G "http://localhost:3100/loki/api/v1/query_range" --data-urlencode 'query={service="worker"}' --data-urlencode "limit=50"
```

## Retention

Loki keeps logs for **7 days** (`retention_period: 168h` in `observability/loki-config.yaml`).

## Windows notes

Promtail needs access to the Docker socket and container log files. **Docker Desktop** supports this; if Promtail shows no logs, ensure containers are running under the same Docker host and project name is `agentcontrol`.

## Stop observability only

```powershell
docker compose -f compose.observability.yaml down
```

Data persists in volumes `lokidata` and `grafanadata` until removed with `docker volume rm`.
