# Observability

## Local Compose dev

Repody emits **JSON logs by default** (`AUDIT_LOG_JSON=true`). With the observability profile, logs land in **Loki** and traces in **Tempo**; Grafana links them by `trace_id`.

```powershell
pnpm dev:all                  # daily driver — observability ON by default
pnpm dev:all -- --no-obs      # skip Grafana/Loki/Tempo/Bugsink
pnpm dev:observability        # observability stack only
pnpm dev:status               # includes Grafana, Loki, Tempo, Bugsink checks
```

| Service | URL |
|---------|-----|
| Grafana | http://localhost:3030 (admin / admin) |
| Loki | http://localhost:3100 |
| Bugsink | http://localhost:8090 (admin@repody.local / repody-dev) |
| OTLP HTTP | http://localhost:4318/v1/traces |

`dev:observability` / `dev:all` writes:

- `backend/.env` — `AUDIT_OTEL_ENABLED`, `AUDIT_LOG_FILE=../.logs/repody-api.log`
- `deploy/env/observability.enabled.env` — worker OTLP (gitignored)
- `.logs/repody-api.log` — host-run API JSON (Promtail → Loki)

**Restart the API** after enabling observability so traces and the log file take effect.

### What ships to Loki

| Source | Label | How |
|--------|-------|-----|
| Compose workers | `compose_service=worker-extract` / `worker-fast` | Docker stdout → Promtail |
| Host API | `compose_service=repody-api` | `.logs/repody-api.log` → Promtail |

### Trace ↔ log correlation

1. API and workers export OTLP traces to the collector → Tempo.
2. Structlog adds `trace_id` / `span_id` to JSON logs when a span is active.
3. In Grafana **Explore → Tempo**, open a trace and use **Logs** (configured in `deploy/observability/grafana/`).

Promtail parses JSON and adds `level` / `service_name` labels for filtering.

Config: `deploy/observability/`.

## Kubernetes

Use **upstream Helm charts** for Loki, Prometheus/Grafana, and OpenTelemetry Collector.

Guide: [docs/deploy/OBSERVABILITY.md](./deploy/OBSERVABILITY.md)

Enable traces on Repody:

```yaml
observability:
  otelEnabled: true
  otelEndpoint: http://otel-collector.observability.svc.cluster.local:4318/v1/traces
```

## Production

Clients ship pod logs and OTLP to their platform. Repody sets `config.logJson: true` in production values.

## Useful log fields

| Field | Role |
|-------|------|
| `event` / `body` | e.g. `repody_vlm_done` |
| `run_id`, `workflow_id` | Audit correlation |
| `trace_id` | OpenTelemetry ↔ Tempo |
| `service.name` | `repody-api`, `repody-worker-extract`, … |

See [BUGSINK.md](./BUGSINK.md) for error tracking in the observability profile.
