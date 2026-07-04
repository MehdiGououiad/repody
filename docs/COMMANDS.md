# Commands

Deploy follows **official upstream docs** — see [docs/deploy/README.md](./deploy/README.md).

## Develop (daily)

| Command | When |
|---------|------|
| `pnpm dev:setup` | **Once** — copy env files, start Compose, migrate |
| `pnpm dev:all` | **Daily** — full stack + API + UI in one terminal |
| `pnpm dev` | Background only — Compose, workers, NuExtract (then exit) |
| `pnpm dev:app` | Foreground API + UI (stack already running) |
| `pnpm dev:status` | Health summary (API, UI, NuExtract, workers) |
| `pnpm dev:stop` | Stop API, UI, NuExtract, and full Compose stack |
| `pnpm dev:restart` | After Vulkan GPU reset — restart NuExtract + workers |
| `pnpm db:migrate` | Apply Alembic migrations |
| `pnpm db:reset` | Drop schema, migrate to head, re-seed demo data |
| `pnpm test:api` | Backend tests (no cluster) |
| `pnpm lint` | Frontend lint |
| `pnpm typecheck` | TypeScript |
| `pnpm doctor` | Toolchain check |

Granular (optional):

| Command | When |
|---------|------|
| `pnpm dev:api` | FastAPI only (`REPODY_API_PORT`, default :8000; reload opt-in with `REPODY_DEV_API_RELOAD=1`) |
| `pnpm ui` | Next.js only (:3000) |
| `pnpm dev:worker` | Both Taskiq worker pools (Docker) |
| `pnpm dev:worker:ocr` | OCR / NuExtract pool only |
| `pnpm dev:worker:fast` | Logic-only pool only |
| `pnpm llamacpp:serve` | NuExtract / llama-server (:8081) |
| `pnpm llamacpp:verify` | Check inference endpoint |

First run:

```powershell
pnpm install
pnpm doctor
pnpm dev:setup
```

Daily:

```powershell
pnpm dev:all
```

Two-terminal split (lighter logs):

```powershell
pnpm dev        # terminal 1 — background
pnpm dev:app    # terminal 2 — API + UI
```

## OpenShift / CRC

[docs/deploy/OPENSHIFT.md](./deploy/OPENSHIFT.md) · Client install: [docs/deploy/CLIENT.md](./deploy/CLIENT.md)

| Command | When |
|---------|------|
| `pnpm openshift:promote` | Vendor CRC bundled smoke (build → deploy → verify) |
| `pnpm openshift:client-ready` | Client-shaped checks on running CRC stack |

## k3s client lab

[docs/deploy/K3S-CLIENT.md](./deploy/K3S-CLIENT.md) — generic Kubernetes client proof (Vault + ESO + Ingress + OTEL).

| Command | When |
|---------|------|
| `pnpm k3s:client` | Full bundled deploy on clean k3d cluster |
| `pnpm k3s:client:clean` | Delete k3d cluster and local registry |

## Enterprise GitOps lab

[docs/deploy/ENTERPRISE-GITOPS.md](./deploy/ENTERPRISE-GITOPS.md) — Harbor + Gitea + Argo CD on k3d.

| Command | When |
|---------|------|
| `pnpm enterprise:lab` | Full vendor→Harbor→GitOps→Argo CD deploy |
| `pnpm enterprise:lab:sync` | Wait for Argo CD Applications healthy |

## Release (vendor → client)

Step-by-step Harbor push and client deploy: [docs/deploy/VENDOR-TO-CLIENT.md](./deploy/VENDOR-TO-CLIENT.md)

Supply chain (SBOM, cosign): [docs/deploy/RELEASE.md](./deploy/RELEASE.md)

```powershell
$env:REPODY_IMAGE_REGISTRY="harbor.yourdomain.com/repody"
$env:REPODY_IMAGE_TAG="1.2.3"
docker login harbor.yourdomain.com
pnpm images:release
pnpm release:attest
pnpm release:promote -- --channel=staging
```

GitHub: push tag `v*` → [images-ghcr.yml](../.github/workflows/images-ghcr.yml) builds, signs, and uploads `dist/release/` artifacts.

Client install: [docs/deploy/CLIENT.md](./deploy/CLIENT.md) · YAML kit: [deploy/client/README.md](../deploy/client/README.md)

## Helm maintenance

| Command | When |
|---------|------|
| `pnpm helm:deps:update` | Refresh chart dependencies |
| `pnpm helm:deps:check` | CI — verify charts/ archives |
| `pnpm helm:lint` | Lint all three charts |
| `pnpm helm:template` | Render app chart |

## Client integration

| Command | When |
|---------|------|
| `pnpm client:check` | Helm render + secrets contract |
| `pnpm deploy:check` | Vendor preflight |
| `pnpm enterprise:secrets` | Validate secret keys in values |

## Tests

| Command | When |
|---------|------|
| `pnpm test:api` | Unit/integration (no cluster) |
| `pnpm test:e2e` | Playwright |
| `pnpm test:platform` | Platform E2E harness |

Production namespace: `repody`. Local Compose uses localhost ports.
