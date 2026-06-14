<!-- BEGIN:nextjs-agent-rules -->
# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` before writing any code. Heed deprecation notices.
<!-- END:nextjs-agent-rules -->

## Platform logs

Do **not** write logs to workspace files. Use Docker or Grafana:

- **Agent debugging:** `docker compose -f compose.yaml -f compose.cpu.yaml -f compose.dev.yaml logs --tail=300 --timestamps worker api` (add `-f` to follow).
- **Human live tail:** `pnpm docker:logs:platform`
- **Human search/history:** Grafana http://localhost:3001 (admin / audit) — dashboard **Platform logs**. Start with `pnpm docker:up:obs` or `pnpm docker:deploy:obs`.

## Dev workflow

- **Fast dev:** `pnpm dev:nowarmup` (or `pnpm dev:warmup` for prod-like model warmup) — see [DEV.md](./DEV.md).
- **Do not** run `docker:up:build` on every code change; rebuild only when `pyproject.toml` or Dockerfiles change.
- **Worker code changes:** `pnpm docker:restart:workers` or `pnpm docker:watch`.
