# Local Harbor registry

[Harbor](https://goharbor.io/) is the local image registry for kind + Helm dev and GitOps testing (`repody-local` Argo CD app).

## Quick start

```powershell
pnpm harbor:bootstrap     # prepare + start Harbor + login + repody project
pnpm k8s:local:hosts      # once — maps *.repody.local → 127.0.0.1 (admin)
pnpm registry:warm        # once — cache third-party images in Harbor
pnpm dev                  # kind + Helm (pushes Repody images to Harbor)
pnpm dev:sync             # daily Skaffold hot-sync loop
```

Harbor UI: http://harbor.repody.lvh.me:8080 (`admin` / password in `paths.harbor.local.env`)

## Configuration

| File | Purpose |
|------|---------|
| `paths.harbor.local.env.example` | Copy → `paths.harbor.local.env` (gitignored) |
| `harbor.yml.example` | Harbor installer template |
| `.runtime/harbor/` | Downloaded installer + data (gitignored) |

Default registry: `harbor.repody.lvh.me:8080/repody` — resolves to localhost without a hosts entry. Override `REPODY_HARBOR_HOST` to `harbor.repody.local` if you use `pnpm k8s:local:hosts` and update `deploy/k8s/kind-repody-local.yaml` mirror host to match.

## Scripts

| Command | Action |
|---------|--------|
| `pnpm harbor:prepare` | Download Harbor installer |
| `pnpm harbor:up` / `harbor:down` | Start / stop Harbor |
| `pnpm harbor:login` | `docker login` to Harbor |
| `pnpm harbor:project` | Create `repody` project |
| `pnpm harbor:connect-kind` | Attach Harbor nginx proxy to kind network |
| `pnpm harbor:bootstrap` | Full Harbor setup |

## GitOps

`repody-local` tracks `deploy/helm/repody` with `values-local-images.yaml` for
promoted Harbor tags. **Synced** means the Git revision Argo CD deployed matches
what is running.

```powershell
# Full loop (build → Harbor → bump tags in Git → push → Argo sync)
pnpm gitops:publish -- --all

# Or step by step
pnpm images:build
pnpm images:push
pnpm gitops:publish -- --commit --push --sync

# After someone else pushed tags
pnpm gitops:sync
```

`pnpm k8s:local` (full stack) uses **git SHA** image tags and bumps
`values-local-images.yaml` locally. Add `--push` to commit/push/sync in the same run.

Daily code edits without a new image: `pnpm dev:sync` (Skaffold).
