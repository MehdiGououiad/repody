# Backend scripts

Run from `backend/` with `uv run python scripts/<name>.py`.

| Script | Purpose |
|--------|---------|
| `docker-entrypoint.sh` | Container entry: optional `alembic upgrade head`, optional OpenTelemetry agent |
| `db_reset.py` | Drop the local database, migrate, seed the demo workflow |
| `export_openapi.py` | Write `lib/api/openapi.json` for the frontend's generated types |
| `generate_facture_fixture.py` | The French invoice PDF used by end-to-end tests |
