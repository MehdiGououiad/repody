# Development workflow

Fast iteration without rebuilding Docker on every code change.

## Quick start (recommended)

### Everything in Docker

Start all containers with a production-built Next.js web server:

```powershell
pnpm platform:start
```

Warm Repody VLM in Docker Model Runner before use:

```powershell
pnpm platform:start:warm
pnpm platform:start -- --models=repody-vlm
```

Stop the container stack:

```powershell
pnpm platform:stop
```

The platform uses **Repody VLM** in Docker Model Runner for document extraction. Downloaded models remain cached when containers stop.

`platform:start` stays attached and streams timestamped logs from every service.
Press `Ctrl+C` to leave the log stream; the containers remain running. Add `--detach`
to return after startup, and reconnect later with `pnpm platform:logs`.

**Fast boot** (no Repody VLM warmup — default for daily use):

```powershell
pnpm dev:nowarmup
```

Starts Docker backend + **production Next.js** on the host (`next build` once, then `node .next/standalone/server.js` on :3000). Skips rebuild if `.next` already exists; use `pnpm dev:rebuild` or `pnpm dev:nowarmup -- --rebuild` after UI changes.

**Prod-like boot** — pulls Repody VLM, warms it in the OCR worker, then starts the production frontend:

```powershell
pnpm dev:warmup
```

Prepare Repody VLM once with `pnpm docker:models:pull:repody-vlm`. Warm startup waits for
`repody_vlm_warmup_done` in worker logs.

Or step by step (use separate lines, or `;` instead of `&&` in older PowerShell):

```powershell
pnpm docker:services
pnpm build    # first time, or after frontend changes
pnpm start
```

Open [http://localhost:3000](http://localhost:3000). API is at [http://localhost:8000](http://localhost:8000).

**Ctrl+C** in the terminal running `pnpm dev:nowarmup` / `pnpm dev:warmup` stops Next.js **and** runs `docker compose down`. To stop manually: `pnpm dev:stop`.

**Note:** The API can take **30–60 seconds** to boot (migrations + Python imports). `pnpm dev:nowarmup` / `pnpm dev:warmup` wait for `/v1/healthz` before starting Next.js. If you start the frontend manually, wait until the API is healthy or run `pnpm docker:wait:api` first.

Copy `.env.example` → `.env.local` for the frontend (defaults already point at `localhost:8000`).

## What reloads automatically

| Change | Action needed | Speed |
|--------|---------------|-------|
| React / TS / CSS (default prod frontend) | `pnpm build` then restart stack (or `pnpm dev:rebuild`) | ~30s–2 min |
| React / TS / CSS (hot reload) | Use `pnpm dev:ui` with backend already running | ~1s (Turbopack) |
| Python API (`backend/src`) | Save file | ~2s (`uvicorn --reload`) |
| Python workers (OCR jobs) | `pnpm docker:restart:workers` | ~10s |
| `pyproject.toml` / Dockerfile | `pnpm docker:build:backend` then `pnpm docker:services` | ~1–3 min (cached) |
| `package.json` | `pnpm install` | ~30s |

## Hot-reload UI development (optional)

When actively editing frontend code, run the Turbopack dev server instead of production:

```powershell
pnpm docker:services
pnpm dev:ui
```

## Worker auto-restart (optional)

Instead of manual restarts after worker edits:

```powershell
pnpm docker:watch
```

Uses [Docker Compose Watch](https://docs.docker.com/compose/how-tos/file-watch/) to sync `backend/src` and restart workers on change. Requires Docker Desktop 4.27+.

## All-in-Docker frontend (optional)

If you prefer not running Node on the host (slower on Windows due to file polling):

```powershell
pnpm docker:up:web-docker
```

Runs Next.js dev server inside Docker with Turbopack. Uses `Dockerfile.web.dev` and a persistent `web_node_modules` volume.

## First boot vs daily restarts

- **First model preparation** downloads and packages Repody VLM for Docker Model Runner.
- **Daily restarts** skip model pulls; `pnpm docker:services` is much faster.
- Dev mode disables Repody VLM warmup on start (`compose.dev.yaml`) for faster API startup unless you use `pnpm dev:warmup`.

## Observability (optional)

Grafana + Loki are **not** started by default in dev. Use the **`obs` module**:

```powershell
pnpm dev:warmup -- --logs              # Loki + Grafana
pnpm dev:warmup -- --traces            # + Tempo / OTEL
pnpm dev:warmup -- --logs --glitchtip  # + GlitchTip (errors module)
```

Or modular Docker: `pnpm platform:up -- --stack=dev-warm --with=obs,errors`

See [docs/PLATFORM.md](./docs/PLATFORM.md) for the full module model.

Grafana: [http://localhost:3001](http://localhost:3001) (admin / audit)

## Commands reference

| Command | Purpose |
|---------|---------|
| `pnpm platform:start` | Build and start the production platform, warming Repody VLM by default |
| `pnpm platform:start -- --models=repody-vlm --detach` | Start without attaching the live log stream |
| `pnpm platform:logs` | Stream timestamped logs from every production service |
| `pnpm platform:start:warm` | Compatibility alias; warms Repody VLM by default |
| `pnpm platform:stop` | Stop the production Docker platform |
| `pnpm containers:start` | Alias for production Docker startup |
| `pnpm containers:start:warm` | Compatibility alias; warms Repody VLM by default |
| `pnpm containers:stop` | Alias for production Docker shutdown |
| `pnpm dev:nowarmup` | Infra + backend + production Next.js (fast boot) |
| `pnpm dev:warmup` | Same, but Repody VLM warmup on start (prod-like) |
| `pnpm dev:rebuild` | Like `dev:nowarmup`, but always runs `next build` |
| `pnpm dev:stop` | Stop Next.js (:3000) and Docker stack |
| `pnpm dev:ui` | Turbopack dev server only (hot reload; backend must be up) |
| `pnpm docker:infra` | Start postgres, redis, and minio |
| `pnpm docker:infra:warmup` | Same infra, for warmup stack |
| `pnpm docker:services` | Start api + workers (no warmup) |
| `pnpm docker:services:warmup` | Start api + workers with Repody VLM warmup |
| `pnpm docker:models:pull` | Pull Repody VLM GGUF and create the optimized local 16K-context variant |
| `pnpm docker:models:pull:repody-vlm` | Same as `docker:models:pull` |
| `pnpm docker:up` | Infra + backend (no build) |
| `pnpm docker:up:build` | Same, rebuild images first |
| `pnpm docker:restart:workers` | Restart OCR + fast workers |
| `pnpm docker:watch` | Auto-restart workers on file change |
| `pnpm docker:build:backend` | Rebuild api/worker images |
| `pnpm docker:logs:platform` | Tail platform container logs |
| `pnpm dev:nowarmup` / `pnpm dev:warmup` | Also streams **all** Docker service logs + `[web]` frontend logs in one terminal |
| `pnpm docker:down` | Stop dev stack |

## Local API without Docker (advanced)

With infra only running:

```powershell
pnpm docker:infra
pnpm dev:api   # uvicorn --reload on host (needs Python 3.12 + backend deps)
pnpm build && pnpm start
```

Set `AUDIT_*` env vars from `.env.example` (use `localhost` for postgres/redis/minio).

## Production deploy

See [DEPLOY.md](./DEPLOY.md).
