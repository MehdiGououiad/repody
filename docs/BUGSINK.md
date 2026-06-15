# Bugsink error tracking

[Bugsink](https://www.bugsink.com/) is self-hosted, Sentry-SDK-compatible error tracking. Repody uses the standard **Sentry SDKs** pointed at your Bugsink DSN.

Compose layout follows the [official Docker Compose install](https://www.bugsink.com/docs/docker-compose-install/) (Postgres + `bugsink/bugsink:2`).

## Quick start (local)

1. Add required Bugsink vars to `.env` (see `.env.example`):

```env
BUGSINK_SECRET_KEY=<openssl rand -base64 50>
BUGSINK_DB_PASSWORD=<strong-password>
# optional — default admin@example.com:admin (email:password)
# BUGSINK_SUPERUSER=you@example.com:your-password
```

2. Start Bugsink:

```powershell
pnpm compose up --modules-only --with=bugsink --detach
```

Or with the dev stack:

```powershell
pnpm compose up --stack=dev --with=bugsink --detach
```

3. Open http://localhost:8090 and sign in with the email/password from `BUGSINK_SUPERUSER` (default `admin@example.com` / `admin`).

4. Create a project and copy its **DSN**.

5. Add DSN vars to `.env`:

```env
BUGSINK_DSN=http://<key>@localhost:8090/<project-id>
NEXT_PUBLIC_BUGSINK_DSN=http://<key>@localhost:8090/<project-id>
BUGSINK_ENVIRONMENT=development
```

6. Rebuild the web app when `NEXT_PUBLIC_BUGSINK_DSN` changes:

```powershell
pnpm dev -- --rebuild
```

## What gets reported

| Surface | SDK | Env var |
|---------|-----|---------|
| Next.js browser | `@sentry/nextjs` (client) | `NEXT_PUBLIC_BUGSINK_DSN` |
| Next.js server / edge | `@sentry/nextjs` | `BUGSINK_DSN` |
| FastAPI + workers | `sentry-sdk` | `BUGSINK_DSN` |

Bugsink does **not** support performance traces, sessions, or client reports — those are disabled in our SDK config.

## Production

- Run Bugsink on its own host or use `pnpm compose up --stack=prod --with=bugsink --build`.
- Set `BUGSINK_BASE_URL` to your public URL (e.g. `https://errors.example.com`).
- Behind HTTPS reverse proxy: set `BUGSINK_BEHIND_HTTPS_PROXY=true` and configure proxy headers per [Bugsink docs](https://www.bugsink.com/docs/docker-compose-install/#reverse-proxy).
- Set `BUGSINK_DSN` on api, workers, and `NEXT_PUBLIC_BUGSINK_DSN` at **web image build** time.
- Kubernetes: `observability.bugsinkDsn` in Helm values (see [CLOUD-K8S.md](./CLOUD-K8S.md)).

## Verify

Throw a test error from the browser devtools console on a page, or call an API route that raises. The issue should appear in the Bugsink project within seconds.

Platform logs remain in **Loki/Grafana** — see [OBSERVABILITY.md](./OBSERVABILITY.md).

## Legacy cleanup (GlitchTip / Sentry / Faro)

If you previously ran GlitchTip on port 8090, stop those containers so they do not conflict with Bugsink:

```powershell
docker ps --filter "name=glitchtip" -q | ForEach-Object { docker stop $_ }
docker ps -a --filter "name=glitchtip" -q | ForEach-Object { docker rm $_ }
```

Remove obsolete env vars from `.env` / `.env.local`:

- `SENTRY_DSN`, `NEXT_PUBLIC_SENTRY_DSN`, `SENTRY_*`
- `GLITCHTIP_*`
- `NEXT_PUBLIC_FARO_*`

Use `BUGSINK_DSN` and `NEXT_PUBLIC_BUGSINK_DSN` only.
