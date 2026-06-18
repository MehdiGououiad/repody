# Development workflow

Daily work on Windows or Linux. For production deploy see [DEPLOY.md](./DEPLOY.md).

## Quick start

```powershell
pnpm install
pnpm dev                  # Docker backend + production Next.js on host
pnpm dev -- --warmup      # same + OCR worker warmup (Repody VLM)
pnpm stop                 # stop host dev + all Repody Docker stacks
```

| URL | Service |
|-----|---------|
| http://localhost:3000 | Web |
| http://localhost:8000 | API |

**Hot-reload UI:** `pnpm ui` (Turbopack) while backend is up.

**All-in-Docker production:** `pnpm prod -- --warmup` · stop with `pnpm stop`

`pnpm stop` tears down host processes on **:3000** and **:8000**, all dev/prod/e2e compose stacks (auth, obs, bugsink variants), then removes any remaining `repody` containers. Use `pnpm stop -- --keep-prod` to leave prod/vps/gpu running; `pnpm stop -- --volumes` also deletes Docker volumes (data wipe).

## Recipe flags

| Flag | Effect |
|------|--------|
| `--warmup` | Pre-load Repody VLM on the OCR worker before use |
| `--rebuild` | Force `next build` |
| `--logs` | Start Grafana/Loki |
| `--traces` | + Tempo / OTEL |
| `--auth` | Keycloak + API OIDC (see **Dev with OIDC** below) |

Bugsink (optional): `pnpm compose up --modules-only --with=bugsink --detach` + DSN in `.env` — [docs/BUGSINK.md](./docs/BUGSINK.md)

Regulated / air-gap: [docs/AIRGAP.md](./docs/AIRGAP.md)
| `--detach` | `pnpm prod` only — exit after start |
| `--auth` | Start Keycloak + OIDC on API (host Next.js still needs `.env.local`) |

### Dev with OIDC (Keycloak)

`pnpm dev` runs Next.js on the **host**; Keycloak runs in Docker. Add to **`.env.local`**:

```env
AUTH_SECRET=<openssl rand -base64 32>
AUTH_KEYCLOAK_ID=repody-web
AUTH_KEYCLOAK_SECRET=repody-web-dev-secret
AUTH_KEYCLOAK_ISSUER=http://127.0.0.1:8080/realms/repody
KEYCLOAK_ADMIN_PASSWORD=admin
```

Then:

```powershell
pnpm dev -- --auth --warmup --logs --rebuild
```

- Web: http://localhost:3000 → redirects to `/login` → Keycloak
- Use **localhost** or **127.0.0.1** in the browser — not `0.0.0.0` (server bind address only). Set `AUTH_URL=http://localhost:3000` in `.env.local` if OAuth redirects break.
- Keycloak admin: http://127.0.0.1:8080/admin (`admin` / `KEYCLOAK_ADMIN_PASSWORD`)
- Test users: `admin@repody.local`, `operator@repody.local`, `viewer@repody.local` — password `repody-dev`
- OIDC smoke (API only): `cd backend && python scripts/auth_oidc_smoke.py`

Without `--auth`, dev runs open (API uses synthetic `platform_admin`, no sign-in).

## Low-level compose

```powershell
pnpm platform:reset              # wipe Postgres, MinIO, Hatchet, local storage
pnpm platform:reset -- --up        # wipe then start dev stack
```

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

## Backend tests

In-process API and service tests use **Postgres + Alembic** (same schema path as production), not SQLite.

```powershell
pnpm compose up --stack=dev --only=infra --detach
cd backend
$env:AUDIT_DATABASE_URL = "postgresql+asyncpg://audit:audit@localhost:5432/audit_workbench_test"
uv run pytest -m "not live" -q
```

The test database is created automatically when missing. Each test gets a clean slate (truncate + seed).

**Live tests** (`@pytest.mark.live`) need the full stack with Hatchet workers — see [docs/E2E.md](./docs/E2E.md).

## Advanced

Host API only: `pnpm compose up --stack=dev --only=infra` then `pnpm dev:api`.

See [docs/PLATFORM.md](./docs/PLATFORM.md) for modules and scaling.
