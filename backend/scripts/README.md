# Backend scripts

Run from repo root via `node scripts/backend-run.mjs --dev python scripts/...` (cwd = `backend/`).

## Ops (keep at this folder root)

Used by containers, CI, and daily development. Paths are stable (`/app/scripts/...` in images).

| Script | Purpose |
|--------|---------|
| `docker-entrypoint.sh` | Container entry |
| `bootstrap_migrations.py` | Alembic upgrade |
| `db_reset.py` | Local DB reset |
| `export_openapi.py` | OpenAPI → `lib/api/openapi.json` |
| `auth_oidc_smoke.py` | Keycloak JWT smoke |
| `platform_integration_suite.py` | Fresh deploy verification |
| `warmup_repody_vlm.py` | One-shot VLM warmup |
| `generate_facture_fixture.py` | E2E Facture PDF |

## Perf / load (same folder — image + kubectl copy paths)

| Script | Purpose |
|--------|---------|
| `load_test_platform.py` | Control-plane + JSON enqueue mix |
| `profile_platform_scale.py` | SQL/EXPLAIN + live enqueue profile |
| `locust_api_load.py` | Locust HTTP mix |
| `benchmark_suite.py` | Operator API benchmarks (also in image) |
| `benchmark_dev_stress.py` | Dev queue stress |
| `benchmark_ui_route.py` | Shared helpers for stress |
| `prod_stress_test.py` | Prod-scale extraction stress (`pnpm stress:prod`) |

Do not move these under a subfolder without updating `Dockerfile`, operator `benchmarks.py`, and `scripts/prod-stress.mjs` pod copy paths.

## Research (`research/`)

Optional research runners: `deploy/scripts/research/` (`qwen35-serve.mjs`).
