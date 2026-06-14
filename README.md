# Repody

Enterprise document audit platform with structured extraction, rule validation, and workflow builder.

## Quick start

```powershell
pnpm install
pnpm platform:start
```

This builds and runs the production Next.js server in Docker and warms Repody VLM by default.
Document extraction uses the pluggable **document model registry** (Repody VLM today; add models in `backend/src/audit_workbench/extraction/model_registry.py`).
Local inference uses **Docker Model Runner** on CPU; GPU deploy uses **official vLLM** (see [DEPLOY.md](./DEPLOY.md)).
Use `--detach` when you want it to return after startup:

```powershell
pnpm platform:start -- --detach
```

Stop everything:

```powershell
pnpm platform:stop
```

For development with Next.js running on the host, use `pnpm dev:nowarmup`.
Use `pnpm dev:ui` for hot reload after the backend containers are running.

See **[DEV.md](./DEV.md)** for the full dev workflow (rebuild, worker watch, optional Docker web).

## Production deploy

```powershell
pnpm docker:deploy
```

See **[DEPLOY.md](./DEPLOY.md)** for GPU, observability, and go-live checklist.

## Docs

- [CONTEXT.md](./CONTEXT.md) — architecture map for tech leads (glossary, lifecycle, registries)
- [DEV.md](./DEV.md) — fast local iteration
- [DEPLOY.md](./DEPLOY.md) — production deployment
- [docs/adr/](./docs/adr/) — architecture decision records
- [docs/OCR_CPU.md](./docs/OCR_CPU.md) — Repody VLM + Docker Model Runner (CPU)
- [docs/REPODY-VLM.md](./docs/REPODY-VLM.md) — on-prem / white-label vLLM
- [docs/OBSERVABILITY.md](./docs/OBSERVABILITY.md) — Grafana / Loki logs
- [docs/E2E.md](./docs/E2E.md) — platform and Playwright tests (CI smoke: `pnpm test:e2e:smoke`)
