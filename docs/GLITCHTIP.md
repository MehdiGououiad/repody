# GlitchTip (Sentry-compatible error tracking)

Self-hosted [GlitchTip](https://glitchtip.com/documentation/install) captures **errors** and a **small slice of API logs**. Full platform logging stays in **Grafana + Loki** — see [OBSERVABILITY.md](./OBSERVABILITY.md).

## Hybrid layout (recommended — what this repo uses)

| Signal | Where | What |
|--------|--------|------|
| All stdout / structlog (api, workers) | **Loki** | `run_id`, `hatchet_run_*`, `repody_vlm_done`, tail/search |
| Exceptions (api, workers, browser) | **GlitchTip** | Stack traces, grouped issues |
| API **warning+** only | **GlitchTip Logs** | `SENTRY_ENABLE_LOGS=true` on api only |
| Worker routine logs | **Loki only** | `SENTRY_ENABLE_LOGS=false` on workers |
| Traces (optional) | **Tempo** | `pnpm docker:deploy:obs` |

Workers are intentionally **not** mirrored to GlitchTip — OCR/Hatchet volume belongs in Loki.

## Start GlitchTip

```powershell
pnpm docker:glitchtip:up
# or (errors module only):
pnpm platform:up -- --modules-only --with=errors --detach
```

Part of the modular platform — see [PLATFORM.md](./PLATFORM.md). Not bundled into the core stack; enable with `--glitchtip` on dev boot or `--with=errors` on `platform:up`.

| | |
|--|--|
| UI | http://localhost:8090 |
| Image | `glitchtip/glitchtip:v6` |
| Compose | `compose.glitchtip.yaml` (`--profile glitchtip`) |

## First-time setup

1. Open http://localhost:8090 and **register**.
2. Create an **organization** and **project**.
3. Copy the project **DSN** (`http://<key>@localhost:8090/1`).

## Wire the platform

Add to `.env`:

```env
SENTRY_DSN=http://<public_key>@localhost:8090/1
NEXT_PUBLIC_SENTRY_DSN=http://<public_key>@localhost:8090/1
SENTRY_ENVIRONMENT=development
# API warning/error lines → GlitchTip Logs (workers stay Loki-only via compose.sentry.yaml)
SENTRY_ENABLE_LOGS=true
SENTRY_LOG_LEVEL=WARNING
GLITCHTIP_SECRET_KEY=generate-a-long-random-string
GLITCHTIP_DOMAIN=http://localhost:8090
```

Restart or rebuild:

```powershell
pnpm dev:nowarmup
# or
pnpm docker:deploy:glitchtip
```

### What each process sends

| Process | GlitchTip errors | GlitchTip logs |
|---------|------------------|----------------|
| **Next.js** | Yes (`@sentry/nextjs`, tunnel `/monitoring`) | No (errors only) |
| **api** | Yes | Warning+ structlog + uvicorn errors |
| **worker / worker-fast** | Yes (uncaught) | No — use Loki |

## Switch to Sentry later

Replace `SENTRY_DSN` / `NEXT_PUBLIC_SENTRY_DSN` with your Sentry ingest URL. No SDK change.

## Related

- [OBSERVABILITY.md](./OBSERVABILITY.md) — Loki, Grafana, Tempo
- [GlitchTip install](https://glitchtip.com/documentation/install)
- [GlitchTip logs](https://glitchtip.com/documentation/logs)
