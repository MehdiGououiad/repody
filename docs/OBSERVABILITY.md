# Observability

## Local (kind cluster)

The local Kubernetes stack includes Grafana, Loki, Promtail, Tempo, and OpenTelemetry wiring via `deploy/k8s/local-addons.yaml` (applied by `pnpm k8s:local`).

| | |
|-|-|
| Grafana | http://grafana.repody.local |
| User | `admin` |
| Password | `audit` |

Requires `pnpm k8s:local:hosts`.

### Pod logs (kubectl)

```powershell
kubectl -n repody logs -l app.kubernetes.io/component=control --tail=200 -f
kubectl -n repody logs -l app.kubernetes.io/component=worker-ocr --tail=200 -f
```

Helm values for local OTEL:

```yaml
observability:
  otelEnabled: true
  otelEndpoint: http://local-tempo:4318/v1/traces
```

## Production

Kubernetes production emits structured JSON to pod stdout. Ship logs to your cluster stack: Loki, CloudWatch, Google Cloud Logging, Azure Monitor, Datadog, or another collector.

```yaml
config:
  logJson: true

observability:
  otelEnabled: true
  otelEndpoint: http://otel-collector.monitoring.svc.cluster.local:4318/v1/traces
```

## Useful log fields

| Field | Example | Role |
|-------|---------|------|
| `event` / `body` | `repody_vlm_done` | Document-model extraction finished |
| `level` | `info` | Log level |
| `run_id` | `run_abc` | Audit run |
| `workflow_id` | `wf_123` | Workflow |
| `request_id` | UUID | HTTP correlation id |
| `trace_id` | hex | OpenTelemetry trace |
| `service.name` | `repody-worker-ocr` | Process |

Sensitive keys are redacted before emit.

## Local Loki queries

```logql
{service="worker"}
```

```logql
{service="worker"} | json | event="repody_vlm_done"
```

```logql
{service=~"api|worker.*"} | json | level="error"
```

## Error tracking

Browser, API, and worker exceptions use Bugsink/Sentry-compatible DSNs. See [BUGSINK.md](./BUGSINK.md).
