# Development

**Local path:** Docker Compose + host processes. **Cluster path:** OpenShift client install (bundled or external) — not a daily dev loop.

All deploy docs: [docs/deploy/README.md](./docs/deploy/README.md)

## Daily workflow (Compose)

```powershell
corepack enable
pnpm install
pnpm doctor
pnpm dev:setup          # once
pnpm dev:all            # daily — stack + API + UI
pnpm test:api
pnpm dev:stop           # stop everything
```

Split logs across two terminals: `pnpm platform` then `pnpm dev:app` (source contribute path).

Details: [docs/deploy/LOCAL.md](./docs/deploy/LOCAL.md) · Mac: [docs/deploy/MAC.md](./docs/deploy/MAC.md) · hub: [docs/README.md](./docs/README.md)

## OpenShift (client production)

Start-to-finish: [docs/deploy/OPENSHIFT.md](./docs/deploy/OPENSHIFT.md) · profiles/detail: [docs/deploy/CLIENT.md](./docs/deploy/CLIENT.md)

## Release images (GHCR / client registry)

[docs/deploy/RELEASE.md](./docs/deploy/RELEASE.md) + `pnpm images:release`

## Command reference

[docs/COMMANDS.md](./docs/COMMANDS.md)
