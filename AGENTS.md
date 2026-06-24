<!-- BEGIN:nextjs-agent-rules -->
# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` before writing any code. Heed deprecation notices.
<!-- END:nextjs-agent-rules -->

## Platform logs

Do **not** write logs to workspace files. Use kubectl or Grafana:

- **Agent debugging:** `kubectl -n repody logs -l app.kubernetes.io/component=control --tail=300 --timestamps` (add `-f` to follow). Workers: label `app.kubernetes.io/component=worker-ocr` or `worker-fast`.
- **Human live tail:** `kubectl -n repody logs -f deploy/repody-api`
- **Human search/history:** Grafana http://grafana.repody.local (admin / audit) — dashboard **Platform logs**. Requires `pnpm k8s:local:hosts` and a running cluster (`pnpm k8s:local`).

## Dev workflow

- **Bootstrap once:** `pnpm dev` — Helm deploy when cluster is new or after `pnpm stop`.
- **Daily loop:** `pnpm dev:sync` — Skaffold hot sync (Python/TS); no full rebuild/re-helm per save.
- **Stop app:** `pnpm stop` — uninstalls Helm release; **keeps** kind + Harbor (fast next `pnpm dev`).
- **Full tear-down:** `pnpm stop:cluster` or `pnpm platform:reset`.
- **Third-party images:** `pnpm registry:warm` once after clone; `pnpm dev` skips Harbor/Docker pulls when cached.
