# Bugsink error tracking

[Bugsink](https://www.bugsink.com/) is self-hosted, Sentry-SDK-compatible error tracking.

## Local Compose dev

Bugsink runs in the **observability** profile (`pnpm dev:all` or `pnpm dev:observability`):

| | |
|--|--|
| URL | http://localhost:8090 |
| Login | admin@repody.local / repody-dev |

**First-time setup**

1. Start observability: `pnpm dev:observability`
2. Open http://localhost:8090 and sign in
3. Create a project (e.g. `repody-local`) and copy the DSN
4. Set DSN in `backend/.env` and `.env.local`:

```env
BUGSINK_DSN=http://<key>@127.0.0.1:8090/<project-id>
NEXT_PUBLIC_BUGSINK_DSN=http://<key>@127.0.0.1:8090/<project-id>
```

5. For **Compose workers**, add the same DSN to repo-root `.env` (Compose interpolation) using `host.docker.internal`:

```env
BUGSINK_DSN=http://<key>@host.docker.internal:8090/<project-id>
```

6. Restart API and recreate workers: `pnpm dev:restart` (workers) + restart API

## Kubernetes

Deploy Bugsink with your observability stack (upstream Helm or compose). See [docs/deploy/OBSERVABILITY.md](./deploy/OBSERVABILITY.md).

Set Helm values for the Repody release:

```yaml
observability:
  bugsinkDsn: http://<key>@bugsink.example.com/<project-id>
```

Rebuild/redeploy web if the browser DSN changes (`NEXT_PUBLIC_BUGSINK_DSN` is baked at image build).

## What gets reported

| Surface | SDK | Env var |
|---------|-----|---------|
| Next.js browser | `@sentry/nextjs` (client) | `NEXT_PUBLIC_BUGSINK_DSN` |
| Next.js server / edge | `@sentry/nextjs` | `BUGSINK_DSN` |
| FastAPI + workers | `sentry-sdk` | `BUGSINK_DSN` |

Bugsink does **not** support performance traces, sessions, or client reports — those are disabled in our SDK config.

## Production

- Run Bugsink as a separate deployment or use a managed Sentry-compatible endpoint.
- Set `BUGSINK_BASE_URL` to your public URL (e.g. `https://errors.example.com`).
- Behind HTTPS: set `BUGSINK_BEHIND_HTTPS_PROXY=true` per [Bugsink docs](https://www.bugsink.com/docs/docker-compose-install/#reverse-proxy).
- Kubernetes: `observability.bugsinkDsn` in Helm values (see [deploy/CLIENT.md](./deploy/CLIENT.md)).

## Verify

Trigger a test error from the browser console or an API route that raises. The issue should appear in the Bugsink project within seconds.

Platform logs remain in your log stack — see [OBSERVABILITY.md](./OBSERVABILITY.md).

## Environment variables

Use `BUGSINK_DSN` and `NEXT_PUBLIC_BUGSINK_DSN` for error tracking. Do not set `SENTRY_*`, `GLITCHTIP_*`, or `NEXT_PUBLIC_FARO_*`.
