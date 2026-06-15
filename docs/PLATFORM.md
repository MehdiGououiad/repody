# Modular platform architecture

Stacks + optional modules. SSOT: [`deploy/platform-modules.mjs`](../deploy/platform-modules.mjs). CLI: `pnpm compose`.

## Modules

| Module | CLI | Purpose |
|--------|-----|---------|
| `infra` | (core) | Postgres, Redis, MinIO, Hatchet |
| `control` | (core) | FastAPI |
| `workers` | (core) | OCR + fast Hatchet pools — **scale here first** |
| `edge` | (core) | Next.js web |
| `obs` | `--with=obs` | Grafana + Loki |
| `traces` | `--with=traces` | Tempo + OTEL (requires obs) |
| `bugsink` | `--with=bugsink` | Self-hosted Bugsink error tracking |

`pnpm compose modules` · `pnpm compose stacks`

## Stacks

| Stack | When |
|-------|------|
| `dev` | Local development |
| `prod` | Single-host production |
| `prod-micro` | Split image tags (K8s / `pnpm images:build`) |
| `vps` | Ubuntu VPS compose chain |
| `gpu` | vLLM inference |
| `e2e` | CI Playwright |

## Overlays (flags on `compose up`)

| Flag | Adds |
|------|------|
| `--warmup` | Repody VLM warmup (`warmup.yaml`; on `dev`, swaps out `dev.yaml`) |
| `--lan` | Office LAN (`lan.yaml`) |
| `--public` | Caddy HTTPS (`public.yaml`) |
| `--scale` | Worker pool tuning (`scale.yaml`) |

## Examples

```powershell
pnpm dev -- --warmup --logs
pnpm compose up --stack=prod --scale --scale-worker=3 --build
pnpm compose up --stack=vps --with=obs,traces --build
pnpm compose scale --stack=prod --scale --worker=3
```

## Optional observability

**Logs/traces:** `pnpm compose up --stack=prod --with=obs,traces --build` or `pnpm dev -- --logs --traces`

**Error tracking (Bugsink):** `pnpm compose up --modules-only --with=bugsink --detach` or set DSN in `.env` — [BUGSINK.md](./BUGSINK.md). Rebuild web after changing `NEXT_PUBLIC_BUGSINK_DSN`.

Grafana: http://localhost:3001 (admin / audit)

## Scale priority

1. `workers` — `--scale-worker=N` with `--scale` overlay
2. `control` — uvicorn workers in `deploy/compose/prod.yaml`
3. `infra` — managed Postgres/Redis before multi-node workers
4. `edge` — CDN / multiple web replicas

## Helm boundary

| Compose module | Helm |
|----------------|------|
| control | `repody-api` |
| workers | worker Deployments + HPA |
| infra | Bitnami charts + Hatchet |
| edge | `repody-web` + Ingress |

[docs/CLOUD-K8S.md](./CLOUD-K8S.md) · [ADR 003](./adr/003-modular-platform-modules.md)
