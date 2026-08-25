# Observability (Kubernetes)

Use upstream Helm charts — no hand-maintained YAML in this repo.

## OpenTelemetry (app traces)

Enable in Repody values:

```yaml
observability:
  otelEnabled: true
  otelEndpoint: http://otel-collector.observability.svc.cluster.local:4318/v1/traces
```

Install collector per [OpenTelemetry Helm charts](https://github.com/open-telemetry/opentelemetry-helm-charts/tree/main/charts/opentelemetry-collector).

## Logs + metrics + dashboards

Recommended stack (pick one):

| Stack | Docs |
|-------|------|
| **Grafana k8s monitoring** | https://grafana.com/docs/grafana-cloud/monitor-infrastructure/kubernetes-monitoring/ |
| **kube-prometheus-stack** | https://github.com/prometheus-community/helm-charts/tree/main/charts/kube-prometheus-stack |
| **Loki stack** | https://grafana.com/docs/loki/latest/setup/install/helm/ |

## Production

Clients own their observability backend. Repody emits JSON logs (`config.logJson: true`) and optional OTLP traces.

1. Deploy a collector (or use an existing platform stack).
2. Set `observability.otelEnabled: true` and `observability.otelEndpoint` in client values.
3. Upgrade the Repody release.

Example collector install (optional; use the client's preferred stack):

```powershell
helm repo add open-telemetry https://open-telemetry.github.io/opentelemetry-helm-charts
helm install otel open-telemetry/opentelemetry-collector -n monitoring
```

See also [docs/OBSERVABILITY.md](../OBSERVABILITY.md) for log fields and queries.
