<!-- BEGIN:nextjs-agent-rules -->
# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` before writing any code. Heed deprecation notices.
<!-- END:nextjs-agent-rules -->

## Commands

[docs/COMMANDS.md](./docs/COMMANDS.md) — **develop** (Compose), **OpenShift client**, **release** (Harbor push).

Daily: `pnpm dev:all` · or `pnpm dev` + `pnpm dev:app` · `pnpm dev:stop`

Deploy guides: [docs/deploy/README.md](./docs/deploy/README.md)

## Platform logs (OpenShift / client cluster)

Do **not** write logs to workspace files:

```powershell
kubectl -n repody logs -l app.kubernetes.io/component=control --tail=300 --timestamps
kubectl -n repody logs -f deploy/repody-api
```

Production namespace: `repody`.
