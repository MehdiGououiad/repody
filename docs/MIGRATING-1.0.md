# Upgrading to Repody 1.0

1.0 changes the API, the stored data and some configuration.

**1.0 starts from a new database.** Its schema is a single migration (`1_0`), so a 0.x database
is not upgraded in place: create an empty database (or drop the old one) and run

```bash
pnpm db:migrate
```

Export anything you need from 0.x first (the audit CSV export works on 0.x). A database that
still has a 0.x revision stops `alembic upgrade` with "Can't locate revision", rather than
running 1.0 on the old tables.

## API

| Change | Before (0.x) | 1.0 |
|--------|--------------|-----|
| Rule condition | `left`, `arithmeticOp`, `leftExtra`, `tableAggregate` side by side | `left` is one of `{"kind": "field", "field"}`, `{"kind": "arithmetic", "op", "left", "right"}`, `{"kind": "aggregate", "fn", "table", "column", "filterColumn", "filterContains"}` |
| Field operand | `{"kind": "field", "value": "total"}` | `{"kind": "field", "field": "total"}` (literals keep `{"kind": "literal", "value"}`) |
| Table columns | lower-cased (`unit_price`) and often unmatched | the schema's own names (`Unit Price`), validated on save |
| Template types | any string | known NuExtract types only (422 otherwise); `GET /v1/catalog` lists them |
| Run progress | `GET /v1/runs/{id}/events` (SSE) | removed: poll `GET /v1/runs/{id}` |
| Progress steps | `label` and `detail` in English | `kind` (`queue`, `extract`, `rules`, `finalize`) and data (`documentType`, `ruleCount`, `fieldsExtracted`, `failed`) |
| Extraction failure | silent (no fields) | `documents[].extraction.error` on the report |
| Audits | `GET /v1/audits?limit&offset` | adds `q`, `outcome`, `workflowId`, `day` |
| Exports | browser-built CSV, 200 rows at most | `GET /v1/audits/export.csv` (every match, streamed), `GET /v1/audits/{id}/export.csv` |
| Dashboard | `audits`, KPI `pendingReview`, weekday names | `recentAudits`, `failedAudits`, no `pendingReview` (see `queue`), ISO dates; pass rate is passed / finished runs |
| Ids | `AUD-` + 12 random hex characters | `run-` + a UUIDv7 in hex: 32 characters, sorted by creation time (existing ids are kept) |
| Starting a run | an unknown workflow answered 404 to anyone | 401 to a caller with neither the workflow's API key nor run permission, whether the workflow exists or not |
| Files and documents | several files could name one workflow document | one file per document (422 otherwise) |
| Test-run `definition` | a bad draft answered one message | FastAPI's validation errors (`detail` is a list with locations) |
| Rate limit (429) | `Retry-After: 60` | `Retry-After` is the seconds until the window frees up (sliding window counter) |
| Archived workflows | their API key still read their runs | an archived workflow's key no longer works |
| Workflow text | unbounded (very long names failed with 500) | names up to 200 characters, descriptions and instructions up to 20 000 (422 beyond) |
| Field names | unique ignoring case | unique as rules read them (`Unit Price` and `unit_price` are one field) |
| Enum fields | fewer than 2 choices failed at run time | at least 2 choices, checked on save |
| `GET /v1/catalog` | field types | adds `operatorsByType` (what each type takes) and `presenceOperators`; the builder offers these |

### Rule evaluation

| Rule | Before (0.x) | 1.0 |
|------|--------------|-----|
| `IN` / `NOT_IN` with one value | a substring test on text (`apple IN pineapple` held), an error on numbers | membership: the value is one of the comma-separated values |
| Dates and times | compared as text (time zones ignored) | parsed as ISO 8601 and compared as dates; an unparseable extracted value counts as missing, an unparseable literal is refused on save |
| List fields (`<type>-list`, `multi-enum`) | `==` and `IN` saved but never matched | only `EXISTS` / `IS_EMPTY` (422 otherwise) |
| Aggregate of a table that was not extracted | `0` (`count_rows_where(t) == 0` passed) | unknown: the rule is skipped |
| `<document type>.<field>` | resolved only when several documents had fields | always resolves; a bare name resolves when exactly one document has the field |
| Answer cut off at the model's token limit | repaired into partial data | `extraction.error`, and its fields are not used |

## Configuration

| Variable | Change |
|----------|--------|
| `BETTER_AUTH_SECRET`, `BETTER_AUTH_URL` | Replace `AUTH_SECRET` and `AUTH_URL` for the web app (Better Auth). Helm and Compose map them for you; the secret store key stays `AUTH_SECRET`. In `.env.local`, rename both. |
| `AUTH_KEYCLOAK_SECRET` | The web app reads only this name. `AUTH_KEYCLOAK_CLIENT_SECRET` remains the name of the deployment secret that Helm maps to it; in `.env.local`, rename it. |
| `AUDIT_INFERENCE_CONCURRENCY` | New (default `1`): model requests in flight per process. Set it to llama-server's `--parallel` to extract documents and pages concurrently. |
| `AUDIT_RUN_RETENTION_DAYS` | New (default `0`, keep everything): finished runs and their files older than this are deleted by maintenance. |
| Scheduler | New process: `taskiq scheduler repody.worker:scheduler`, exactly one replica (Helm `repody-scheduler`, Compose `scheduler`). It sends the maintenance task every `AUDIT_MAINTENANCE_INTERVAL_SECONDS`; the API no longer runs maintenance. |
| `pnpm platform` flags | `--no-vlm` and `--no-observability` are gone: use `--no-nuextract` and `--no-obs`. Unknown flags are now an error. |
| `AUDIT_OIDC_AUDIENCE` | Required in production: tokens issued to other clients of the realm are refused. Keycloak access tokens only (`typ: Bearer`), never ID tokens. |
| `AUDIT_CORS_ORIGINS` | Default is now empty (no CORS): the web app calls the API through its own server. Set it only for browser apps on other origins; credentials are never allowed. |
| `AUDIT_S3_REGION` | New (default `us-east-1`). Compose storage is SeaweedFS on `:8333` (`repody` / `s3-local-dev`), replacing the MinIO fork. |
| `AUDIT_HEALTH_TIMEOUT_SECONDS` | New (default `2`): `/v1/healthz` reports a dependency down when it does not answer in time. |
| Numeric limits | Negative values are refused (`AUDIT_MAX_UPLOAD_BYTES`, `AUDIT_MAINTENANCE_INTERVAL_SECONDS`, ...). |
| Mac runtime | Removed (`deploy/client/mac-runtime` and its packaging script). |
| Helm `ingress.filesHost` / `filesService` | Removed (the API never issued presigned uploads). |

## Sign-in

Auth.js is replaced by Better Auth (generic OAuth with Keycloak), stateless: the session and the
Keycloak tokens live in encrypted `better-auth.*` cookies, no database. Everyone signs in again once.
The Keycloak callback stays `/api/auth/callback/keycloak`, so the realm needs no change.
`/logout` ends the session and returns to the login page.

The web app now takes every Keycloak endpoint from its discovery document and verifies the ID
token against Keycloak's keys. When it reaches Keycloak by an internal URL
(`AUTH_KEYCLOAK_INTERNAL_ISSUER`, Helm `web.internalIssuer`), Keycloak must name its
server-to-server endpoints on that host: run it with hostname v2, `KC_HOSTNAME` set to the full
public URL and `KC_HOSTNAME_BACKCHANNEL_DYNAMIC=true`
([Keycloak hostname guide](https://www.keycloak.org/server/hostname)). Compose does this for you.
The hostname v1 options `KC_HOSTNAME_STRICT_HTTPS` and a bare `KC_HOSTNAME: localhost` are gone.

## Web app

- Theme follows the system until changed (next-themes); the `wb_theme` cookie is no longer read.
- Dates are shown in the reader's time zone, reported once by the browser (`wb_tz` cookie).
- Audit filters live in the URL (`?q=&outcome=&workflow=&day=&page=`); `?status=` is now `?outcome=`.
- A workflow API key is shown once, on deploy; it is no longer kept in session storage.

## Postgres 18

Compose and the CloudNativePG example move from Postgres 17 to 18. Postgres data files do not cross
major versions, so the local stacks use a new volume (`repody-postgres-18`, mounted at
`/var/lib/postgresql` as the official 18 image expects) and keep the 17 one. To bring local data
across, dump from 17 and restore into 18
([PostgreSQL upgrading](https://www.postgresql.org/docs/18/upgrading.html)):

```bash
docker compose stop api worker scheduler web
docker run -d --name repody-pg17 -e POSTGRES_PASSWORD=unused -v repody_repody-postgres:/var/lib/postgresql/data postgres:17.11-alpine
docker exec repody-pg17 pg_dumpall -U audit > repody-pg17.sql
docker rm -f repody-pg17
docker compose up -d --wait postgres
docker compose exec -T postgres psql -U audit -d postgres -f - < repody-pg17.sql
pnpm db:migrate
```

On Kubernetes, CloudNativePG upgrades the major version in place when `imageName` changes
([CloudNativePG: major upgrades](https://cloudnative-pg.io/documentation/current/postgres_upgrades/)).
Take a backup first.
