# Observability

## Local Compose dev

Structured logs go to the terminal running `pnpm dev:api` / workers. No in-repo log stack.

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
| `trace_id` | OpenTelemetry |
| `service.name` | `repody-api`, `repody-worker-ocr`, … |

See [BUGSINK.md](./BUGSINK.md) for error tracking (client-managed DSN).
