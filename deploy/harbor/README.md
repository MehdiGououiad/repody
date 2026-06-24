# Local Harbor registry

Real [Harbor](https://goharbor.io/) for prod-path testing instead of the `registry:2` container on `localhost:5001`.

## Quick start

```powershell
pnpm harbor:bootstrap    # download installer, start Harbor, create repody project
pnpm k8s:local:hosts     # adds harbor.repody.local (admin)
pnpm dev:harbor          # kind + Helm using Harbor as image registry
pnpm harbor:connect-kind # attach Harbor proxy to kind network (also runs during dev:harbor)
```

Harbor UI: http://harbor.repody.local:8080 — `admin` / `Harbor12345` (change in `paths.harbor.local.env`).

## vs simple registry

| | Simple (`pnpm dev`) | Harbor (`pnpm dev:harbor`) |
|---|---|---|
| Registry | `localhost:5001` (`kind-registry`) | `harbor.repody.local:8080/repody` |
| Setup | automatic | `pnpm harbor:bootstrap` once |
| kind config | `kind-repody-local.yaml` | `kind-repody-local-harbor.yaml` |

Mode is selected via `deploy/harbor/paths.harbor.local.env` (`REPODY_REGISTRY_MODE=harbor`) or `REPODY_REGISTRY_MODE` env var.

## Files

- `harbor.yml.example` — copied to `.runtime/harbor/harbor.yml` on prepare (HTTP on **8080** to avoid Envoy on :80)
- `paths.harbor.local.env.example` — copied to `paths.harbor.local.env` on prepare
- `.runtime/` — installer download + Harbor data (gitignored)

## Requirements

- Docker Desktop
- **bash** (Git Bash or WSL on Windows) for first-time `install.sh`
- `curl` for health checks

## Commands

| Command | Description |
|---------|-------------|
| `pnpm harbor:prepare` | Download Harbor installer + config |
| `pnpm harbor:up` | Start Harbor (`docker compose up -d`) |
| `pnpm harbor:down` | Stop Harbor |
| `pnpm harbor:login` | `docker login` to Harbor |
| `pnpm harbor:project` | Create public `repody` project |
| `pnpm harbor:connect-kind` | Connect Harbor nginx to `kind` network |
| `pnpm harbor:bootstrap` | prepare + up + wait + login + project |

Docs: https://goharbor.io/docs/latest/install-config/
