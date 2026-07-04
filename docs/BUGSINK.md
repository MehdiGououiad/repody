# Bugsink error tracking

[Bugsink](https://www.bugsink.com/) is self-hosted, Sentry-SDK-compatible error tracking.

## Local Compose dev

Bugsink is **not** bundled in Compose. Use client-managed Bugsink or skip error tracking locally.

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
