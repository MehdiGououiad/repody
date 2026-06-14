# Kubernetes / cloud deployment

Deploy the Repody audit platform on Kubernetes with Helm. This mirrors the modular Compose stacks (`infra`, `control`, `workers`, `edge`) as separate Deployments and uses in-cluster Postgres, Redis, MinIO, and Hatchet Lite by default.

See [ADR 004](./adr/004-cloud-kubernetes-packaging.md) for decisions.

## Prerequisites

- Kubernetes 1.28+ cluster
- `kubectl` configured
- `helm` 3.14+
- Container registry (GHCR, ECR, ACR, etc.)
- Ingress controller (e.g. nginx) if using `ingress.enabled`
- **GPU inference** — external vLLM service (not bundled in this chart)

## 1. Build and push images

```bash
export REGISTRY=ghcr.io/YOUR_ORG
export TAG=0.1.0

pnpm platform:images:build
pnpm platform:images:push
```

Images:

| Image | Role |
|-------|------|
| `audit-api` | FastAPI control plane |
| `audit-worker` | Hatchet workers (ocr + fast pools) |
| `audit-web` | Next.js edge |

## 2. Fetch Helm dependencies

```bash
pnpm helm:deps
```

Downloads Bitnami subcharts (PostgreSQL, Redis, MinIO).

## 3. Configure values

Copy and edit production overrides:

```bash
cp deploy/helm/audit-platform/values-production.yaml.example my-values.yaml
```

Required settings:

- `secrets.adminApiToken` — strong random token for admin API / web proxy
- `images.*.repository` / `tag` — your registry paths
- `ingress.host` / `ingress.tls` — public UI hostname
- `config.vllmBaseUrl` — reachable vLLM OpenAI-compatible endpoint
- `config.corsOrigins` — JSON array matching your UI origin

Optional:

- `hatchet.clientToken` — skip bootstrap Job if you already have a token
- `observability.sentryDsn` — GlitchTip / Sentry DSN

## 4. Install

```bash
helm upgrade --install audit deploy/helm/audit-platform \
  -n audit --create-namespace \
  -f my-values.yaml \
  --set secrets.adminApiToken="$(openssl rand -hex 32)"
```

Dry-run:

```bash
pnpm helm:template -- -f my-values.yaml
```

## 5. Verify

```bash
kubectl -n audit get pods
kubectl -n audit logs job/audit-audit-platform-hatchet-token-bootstrap  # if bootstrap enabled
kubectl -n audit port-forward svc/audit-audit-platform-web 3000:3000
```

Hatchet bootstrap Job creates `audit-audit-platform-hatchet-token` Secret. API and workers wait for this secret before starting.

## Scaling

Worker pools scale via Helm values or HPA:

```yaml
workerOcr:
  autoscaling:
    enabled: true
    minReplicas: 2
    maxReplicas: 20
```

```bash
helm upgrade audit deploy/helm/audit-platform -f my-values.yaml \
  --set workerOcr.replicas=5
```

API and web have fixed replica counts in values; enable `api.autoscaling` when template is extended.

## Managed data plane

Disable in-cluster charts and point at managed services:

```yaml
postgresql:
  enabled: false
externalDatabase:
  enabled: true
  url: postgresql+asyncpg://user:pass@rds-host:5432/audit_workbench

redis:
  enabled: false
externalRedis:
  enabled: true
  url: rediss://...

minio:
  enabled: false
externalObjectStorage:
  enabled: true
  endpoint: s3.amazonaws.com
  bucket: my-bucket
  accessKey: ...
  secretKey: ...
  publicEndpoint: files.example.com
```

## Compose parity (microservices)

For Docker-based prod with split images:

```bash
REGISTRY=ghcr.io/YOUR_ORG TAG=0.1.0 pnpm platform:up -- --stack=prod-scale --build
```

Prod stacks include `compose.microservices.yaml` for separate `audit-api` / `audit-worker` tags.

## Observability on K8s

- **Logs**: ship container stdout to your cluster log stack (Loki, CloudWatch, etc.); `AUDIT_LOG_JSON=true` is set by default.
- **Errors**: set `observability.sentryDsn` for GlitchTip/Sentry on api + web.
- **Traces**: set `observability.otelEnabled=true` and `otelEndpoint` when you run an OTLP collector.

## Troubleshooting

| Symptom | Check |
|---------|--------|
| API stuck init | Hatchet token secret empty — logs from `hatchet-token-bootstrap` Job |
| Workers OOM | Raise `workerOcr.resources.limits.memory` (VLM warmup) |
| Upload failures | MinIO ingress `filesHost` + `AUDIT_MINIO_PUBLIC_ENDPOINT` |
| Inference errors | `config.vllmBaseUrl` from worker pods (`kubectl exec` curl) |

## Related

- [PLATFORM.md](./PLATFORM.md) — Compose modules and stacks
- [GLITCHTIP.md](./GLITCHTIP.md) — error tracking setup
- [OBSERVABILITY.md](./OBSERVABILITY.md) — Loki/Grafana on Compose
