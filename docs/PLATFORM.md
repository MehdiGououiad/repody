# Modular platform architecture

Scale-first deployment model: **stack presets** + **optional modules**. Each module is an independently deployable unit (future microservice / Helm chart boundary).

## Modules

```text
┌─────────────┐     ┌─────────────┐     ┌──────────────────┐
│    edge     │────▶│   control   │────▶│      infra       │
│  (Next.js)  │     │  (FastAPI)  │     │ pg/redis/minio/  │
└─────────────┘     └──────┬──────┘     │     hatchet      │
                           │            └────────┬─────────┘
                           ▼                     │
                    ┌─────────────┐              │
                    │   workers   │◀─────────────┘
                    │ ocr + fast  │  (Hatchet pull)
                    └─────────────┘

Addons (optional):  obs (Loki)  |  traces (Tempo)  |  errors (GlitchTip)
```

| Module | CLI id | Purpose |
|--------|--------|---------|
| Infrastructure | `infra` | Data + queue plane |
| Control plane | `control` | API, dispatch, auth |
| Worker plane | `workers` | Run execution (**scale here first**) |
| Edge | `edge` | Web UI |
| Logs | `obs` | Grafana + Loki |
| Traces | `traces` | Tempo + OTEL |
| Errors | `errors` | GlitchTip |

List modules: `pnpm platform:modules`

## Stack presets

| Preset | Use |
|--------|-----|
| `dev` | Fast boot, host or Docker backend |
| `dev-warm` | Repody VLM warmup |
| `prod` | Production images + web |
| `prod-scale` | Production + scale-friendly pool settings |
| `gpu` | vLLM inference overlay |

List stacks: `pnpm platform:stacks`

## Common commands

### Dev: warmup + Loki + GlitchTip (one command)

```powershell
pnpm dev:warmup -- --logs --glitchtip
```

Set `SENTRY_DSN` / `NEXT_PUBLIC_SENTRY_DSN` in `.env` for error reporting.

### Modular Docker up (prod-scale + observability + errors)

```powershell
pnpm platform:up -- --stack=prod-scale --with=obs,errors --build
```

### Scale workers only (no api/web rebuild)

```powershell
pnpm platform:scale -- --stack=prod-scale --worker=3 --worker-fast=2
```

### Addon only (GlitchTip)

```powershell
pnpm platform:up -- --modules-only --with=errors
```

### Logs

```powershell
pnpm platform:logs -- --stack=dev-warm --with=obs
```

## Scale priority

1. **`workers` module** — `docker compose --scale worker=N` (OCR pool) and `worker-fast=N` (logic pool). Use `prod-scale` preset for tuned DB/Redis pools.
2. **`control` module** — increase uvicorn workers in `compose.prod.yaml` (already `--workers 2`).
3. **`infra` module** — managed Postgres/Redis/S3 before multi-node workers.
4. **`edge` module** — CDN / multiple web replicas behind a load balancer.

Hatchet dispatches to labeled worker pools (`ocr`, `fast`); scaling replicas increases throughput without code changes.

## Microservices path

| Today (Compose module) | Kubernetes (Helm) |
|------------------------|-------------------|
| `control` | `audit-api` Deployment |
| `workers` | `audit-worker-ocr` / `audit-worker-fast` Deployments + HPA |
| `infra` | Bitnami Postgres/Redis/MinIO + Hatchet Lite (or managed overrides) |
| `edge` | `audit-web` Deployment + Ingress |
| `obs` / `traces` / `errors` | Cluster logging + `observability.sentryDsn` |

See [CLOUD-K8S.md](./CLOUD-K8S.md) for install steps. Prod Compose stacks include `compose.microservices.yaml` for split image tags (`audit-api`, `audit-worker`, `audit-web`).

Module IDs and service lists are defined in `deploy/platform-modules.mjs`.

## Related

- [ADR 003](./adr/003-modular-platform-modules.md)
- [ADR 004](./adr/004-cloud-kubernetes-packaging.md)
- [CLOUD-K8S.md](./CLOUD-K8S.md)
- [DEV.md](../DEV.md) — daily workflow
- [OBSERVABILITY.md](./OBSERVABILITY.md) — Loki/Grafana
- [GLITCHTIP.md](./GLITCHTIP.md) — error tracking
