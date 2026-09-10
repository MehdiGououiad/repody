# Scripts map

Repody keeps three script roots on purpose. Prefer this map over dumping new helpers at the repo root.

| Location | Owns | Examples |
|----------|------|----------|
| `scripts/` | Cross-cutting Node helpers invoked from `package.json` | `backend-run.mjs`, `wait-for-api.mjs`, `run-platform-e2e.mjs`, `prepare-standalone.mjs` |
| `deploy/scripts/` | Compose / platform / model serve / release | `platform-dev.mjs`, `local-dev.mjs`, `build-images.mjs`, `research/qwen35-serve.mjs` |
| `backend/scripts/` | Python ops next to the API package | OpenAPI export, DB reset, benchmarks, Locust |

## Rules of thumb

1. If `package.json` calls it with `node scripts/…`, it belongs in `scripts/`.
2. If it boots Docker, Helm, llama-server, or GHCR release, it belongs in `deploy/scripts/`.
3. If it imports `repody` or needs the uv env, it belongs in `backend/scripts/` and is usually run via `node scripts/backend-run.mjs …`.

Research model runners live under `deploy/scripts/research/` with config in `deploy/research/` (currently Qwen 3.5 only).
