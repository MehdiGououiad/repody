# Deploy layout

| Path | Role |
|------|------|
| [`platform-modules.mjs`](./platform-modules.mjs) | Stacks, modules, overlays (SSOT) |
| [`compose/`](./compose/) | Docker Compose YAML |
| [`stacks/*.files`](./stacks/) | Generated lists for VPS bash |
| [`scripts/`](./scripts/) | `compose.mjs`, validation, image build, air-gap |
| [`airgap/`](./airgap/) | Regulated-release manifest |
| [`ENV.md`](./ENV.md) | Secrets and `AUDIT_*` variables |
| [`cloud/`](./cloud/) | VPS scripts |
| [`helm/repody/`](./helm/repody/) | Kubernetes chart |

## Commands

```bash
pnpm dev | prod | stop          # recipes
pnpm compose …                  # low-level stacks/modules
pnpm deploy:check               # CI validation
pnpm deploy:sync-stacks         # refresh stacks/*.files
```

## VPS (one entry per task)

| Task | Script |
|------|--------|
| **First install** | `bash deploy/cloud/deploy.sh` |
| **Update code** | `bash deploy/cloud/bootstrap.sh` |
| **Generate secrets** | `bash deploy/cloud/setup-env.sh` |
| **Validate scripts** | `bash deploy/cloud/validate.sh` |

Shared helpers: `deploy/cloud/lib.sh` (compose file chain from `deploy/stacks/vps.files`).

## Stacks

`dev` · `prod` · `prod-micro` · `vps` · `gpu` · `e2e`

Overlays: `--warmup` `--lan` `--public` `--scale`  
Modules: `--with=obs,traces,bugsink`

See [DEPLOY.md](../DEPLOY.md) and [docs/PLATFORM.md](../docs/PLATFORM.md).
