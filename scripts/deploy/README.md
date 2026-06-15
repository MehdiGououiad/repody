# Legacy deploy scripts

Moved to [`deploy/cloud/`](../../deploy/cloud/):

| Script | Purpose |
|--------|---------|
| [`validate.sh`](../../deploy/cloud/validate.sh) | Shell syntax + bcrypt upsert safety (CI / `pnpm deploy:check`) |
| [`deploy.sh`](../../deploy/cloud/deploy.sh) | First-time VPS install |
| [`bootstrap.sh`](../../deploy/cloud/bootstrap.sh) | Update existing VPS |

Optional local smoke test: [`test-vps-ubuntu.sh`](./test-vps-ubuntu.sh) (runs `deploy.sh` in Ubuntu container).

Compose SSOT: [`deploy/platform-modules.mjs`](../../deploy/platform-modules.mjs) · CLI: `pnpm compose help`
