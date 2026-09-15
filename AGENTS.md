<!-- BEGIN:nextjs-agent-rules -->
# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` before writing any code. Heed deprecation notices.
<!-- END:nextjs-agent-rules -->

## Docs

**Hub:** [docs/README.md](./docs/README.md) · **Commands:** [docs/COMMANDS.md](./docs/COMMANDS.md)

Daily: `pnpm platform` · once: `pnpm platform setup` · stop: `pnpm platform stop` · contributors: `pnpm dev:src:all`

Guides: [docs/LOCAL.md](./docs/LOCAL.md) · [docs/CLUSTER.md](./docs/CLUSTER.md) · architecture: [CONTEXT.md](./CONTEXT.md)

## Platform logs (OpenShift / client cluster)

Do **not** write logs to workspace files:

```powershell
kubectl -n repody logs -l app.kubernetes.io/component=control --tail=300 --timestamps
kubectl -n repody logs -f deploy/repody-api
```

Production namespace: `repody`.
