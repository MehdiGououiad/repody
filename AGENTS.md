<!-- BEGIN:nextjs-agent-rules -->
# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` before writing any code. Heed deprecation notices.
<!-- END:nextjs-agent-rules -->

## Platform logs

Do **not** write logs to workspace files. Use Docker or Grafana:

- **Agent debugging:** `pnpm compose logs --stack=dev` (add `-f` via compose logs, or `docker compose -f deploy/compose/base.yaml -f deploy/compose/cpu.yaml -f deploy/compose/dev.yaml logs --tail=300 --timestamps worker api`).
- **Human live tail:** `pnpm compose logs --stack=dev`
- **Human search/history:** Grafana http://localhost:3001 (admin / audit) — dashboard **Platform logs**. Start with `pnpm compose up --stack=dev --with=obs --only=obs --detach` or `pnpm compose up --stack=prod --with=obs,traces --build`.

## Dev workflow

- **Fast dev:** `pnpm dev` (add `-- --warmup` to pre-load Repody VLM on the OCR worker) — see [DEV.md](./DEV.md).
- **Do not** rebuild images on every code change; rebuild only when `pyproject.toml` or Dockerfiles change (`pnpm compose build --stack=dev --only=backend`).
- **Worker code changes:** `pnpm compose restart workers --stack=dev` or `pnpm compose watch --stack=dev`.
