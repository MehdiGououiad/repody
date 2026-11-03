# Backend scripts

Run from repo root via `uv run --directory backend --extra dev python scripts/...` (cwd = `backend/`).

## Ops (keep at this folder root)

Used by containers, CI, and daily development. Paths are stable (`/app/scripts/...` in images).

| Script | Purpose |
|--------|---------|
| `docker-entrypoint.sh` | Container entry |
| `bootstrap_migrations.py` | Alembic upgrade |
| `db_reset.py` | Local DB reset |
| `export_openapi.py` | OpenAPI -> `lib/api/openapi.json` |
| `auth_oidc_smoke.py` | Keycloak JWT smoke |
| `platform_integration_suite.py` | Fresh deploy verification |
| `warmup_repody_vlm.py` | One-shot VLM warmup |
| `generate_facture_fixture.py` | E2E Facture PDF |
| `generate_bank_statement_fixture.py` | Fictional two-page bank statement PDF for list and object-array extraction tests |

## Load testing

`locust_api_load.py` is a [Locust](https://docs.locust.io/) file for the HTTP API:

```bash
uv run --directory backend --extra dev locust -f scripts/locust_api_load.py --host http://127.0.0.1:8000
```
