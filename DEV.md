# Development workflow

Daily work on Windows or Linux. For production deploy see [DEPLOY.md](./DEPLOY.md).

## Quick start

```powershell
pnpm install
pnpm dev                  # Docker backend + production Next.js on host
pnpm dev -- --warmup      # same + Repody VLM warmup
pnpm stop                 # stop :3000 + Docker
```

| URL | Service |
|-----|---------|
| http://localhost:3000 | Web |
| http://localhost:8000 | API |

**Hot-reload UI:** `pnpm ui` (Turbopack) while backend is up.

**All-in-Docker production:** `pnpm prod -- --warmup` · stop with `pnpm stop -- --prod`

## Recipe flags

| Flag | Effect |
|------|--------|
| `--warmup` | Repody VLM warmup before use |
| `--rebuild` | Force `next build` |
| `--logs` | Start Grafana/Loki |
| `--traces` | + Tempo / OTEL |

Bugsink (optional): `pnpm compose up --modules-only --with=bugsink --detach` + DSN in `.env` — [docs/BUGSINK.md](./docs/BUGSINK.md)

Regulated / air-gap: [docs/AIRGAP.md](./docs/AIRGAP.md)
| `--detach` | `pnpm prod` only — exit after start |

## Low-level compose

```powershell
pnpm compose up --stack=dev --only=infra
pnpm compose up --stack=dev --only=services
pnpm compose restart workers --stack=dev
pnpm compose watch --stack=dev
pnpm compose help
```

Overlays on any stack: `--warmup`, `--lan`, `--public`, `--scale`  
Modules: `--with=obs,traces,bugsink`

## What reloads automatically

| Change | Action |
|--------|--------|
| React / TS (prod path) | `pnpm build` or `pnpm dev -- --rebuild` |
| React / TS (hot) | `pnpm ui` |
| Python API | auto (`uvicorn --reload` in dev stack) |
| Workers | `pnpm compose restart workers --stack=dev` |
| Dockerfile / pyproject | `pnpm compose build --stack=dev --only=backend` |

## Advanced

Host API only: `pnpm compose up --stack=dev --only=infra` then `pnpm dev:api`.

See [docs/PLATFORM.md](./docs/PLATFORM.md) for modules and scaling.
