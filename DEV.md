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

Split logs across two terminals: `pnpm dev` then `pnpm dev:app`.

Details: [docs/deploy/LOCAL.md](./docs/deploy/LOCAL.md)

## OpenShift (client install or CRC lab)

| Need | Guide |
|------|--------|
| Client production on OpenShift | [docs/deploy/CLIENT.md](./docs/deploy/CLIENT.md) + [docs/deploy/OPENSHIFT.md](./docs/deploy/OPENSHIFT.md) |
| Vendor OpenShift client test | `pnpm openshift:client-test` — [OPENSHIFT.md](./docs/deploy/OPENSHIFT.md#client-test-lab) |

## Release images (GHCR / client registry)

[docs/deploy/RELEASE.md](./docs/deploy/RELEASE.md) + `pnpm images:release`

## Command reference

[docs/COMMANDS.md](./docs/COMMANDS.md)
