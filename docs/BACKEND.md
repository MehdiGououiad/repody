# Repody — Python API

Production backend for Repody (Phase 2).

**Step-by-step history:** [BACKEND_STEPS.md](./BACKEND_STEPS.md) (archived)

## Quick start (local, inline jobs)

```bash
# Terminal 1 — database
pnpm compose up --stack=dev --only=infra --detach

# Terminal 2 — API
cd backend
pip install -e ".[dev]"
set AUDIT_DATABASE_URL=postgresql+asyncpg://audit:audit@localhost:5432/audit_workbench
set AUDIT_RUN_JOBS_INLINE=true
set AUDIT_SEED_ON_STARTUP=true
uvicorn audit_workbench.main:app --reload --port 8000

# Terminal 3 — Next.js (proxies /api/* → :8000/v1/*)
cd ..
pnpm dev
```

## Full stack (API + Hatchet workers + MinIO)

```bash
pnpm compose up --stack=dev --build
```

Runs `api`, `worker`, `worker-fast`, and `hatchet-lite` with `AUDIT_RUN_JOBS_INLINE=false`. Upload files via `POST /v1/uploads` or multipart `POST /v1/workflows/{id}/runs`.

## Migrations

```bash
cd backend
python -m alembic upgrade head
```

## Tests

```bash
cd backend
python -m pytest tests/ -v -m "not live"
# or: pnpm test:api
# API E2E suite: pnpm test:api:e2e
# live stack: pnpm test:api:live
# full platform: pnpm test:platform
```

## Environment

Copy `.env.example` at the repo root. All backend settings use the `AUDIT_` prefix.
