# Commands

Deploy follows **official upstream docs** — see [docs/deploy/README.md](./deploy/README.md).

## Develop (daily)

| Command | When |
|---------|------|
| `pnpm dev:setup` | **Once** — copy env files, start Compose, migrate |
| `pnpm dev:all` | **Daily** — full stack + API + UI (add `-- --obs` for Grafana/Loki/Tempo/Bugsink) |
| `pnpm dev` | Background only — Compose, workers, NuExtract (then exit) |
| `pnpm dev:app` | Foreground API + UI (stack already running) |
| `pnpm dev:status` | Health summary (API, UI, NuExtract, workers, Grafana, Loki, Bugsink) |
| `pnpm dev:stop` | Stop API, UI, NuExtract, and full Compose stack |
| `pnpm dev:observability` | Grafana + Loki + Tempo + OTEL + Bugsink (optional profile) |
| `pnpm dev:restart` | After Vulkan GPU reset — restart NuExtract + workers |
| `pnpm db:migrate` | Apply Alembic migrations |
| `pnpm db:reset` | Drop schema, migrate to head, re-seed demo data |
| `pnpm dev:reset` | **Nuclear** — wipe Compose volumes, reset DB, rebuild workers |
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
| `pnpm dev:worker:extract` | Document-model extraction pool only |
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

## OpenShift client test

[docs/deploy/OPENSHIFT.md](./deploy/OPENSHIFT.md) · Production client: [docs/deploy/CLIENT.md](./deploy/CLIENT.md)

Requires `kubectl` + `helm` + `docker` logged in to an OpenShift cluster (kubeconfig).

| Command | When |
|---------|------|
| `pnpm openshift:infra` | **Once** — Harbor, Vault, ESO, OTEL, Argo CD (independent of Repody) |
| `pnpm openshift:e2e` | **Repeat** — build → push → seed → sync → verify → logs |
| `pnpm openshift:client-test` | Full run: infra + e2e (GitOps default; add `--clean` to reset) |
| `pnpm openshift:client-test:external` | External profile |
| `pnpm openshift:client-test:helm` | Direct Helm instead of Argo CD |
| `pnpm openshift:preflight` | Check kubectl, helm, docker |
| `pnpm openshift:client-ready` | Production-shaped validation on running lab |

Flags: `--registry=harbor|openshift` · `--helm` · `--clean` · `--skip-images` · `--skip-build` · `--vlm`

Fast iteration (infra stays up):

```powershell
pnpm openshift:infra
pnpm openshift:e2e --skip-build    # push + sync only
```

## Release (vendor → client)

Step-by-step image push and client deploy: [docs/deploy/VENDOR-TO-CLIENT.md](./deploy/VENDOR-TO-CLIENT.md)

Supply chain (SBOM, cosign): [docs/deploy/RELEASE.md](./deploy/RELEASE.md)

```powershell
$env:REPODY_IMAGE_REGISTRY="ghcr.io/yourorg/repody"
$env:REPODY_IMAGE_TAG="1.2.3"
docker login ghcr.io
pnpm images:release
pnpm release:attest
pnpm release:promote -- --channel=staging
```

GitHub: push tag `v*` → [images-ghcr.yml](../.github/workflows/images-ghcr.yml) builds, signs, and uploads `dist/release/` artifacts.

Client install: [docs/deploy/CLIENT.md](./deploy/CLIENT.md) · YAML kit: [deploy/client/README.md](../deploy/client/README.md)

## Security scanning

Dual-scanner CI: Trivy (primary gate) + Grype on Syft SBOMs. Full comparison: [deploy/security/README.md](../deploy/security/README.md).

| Command | When |
|---------|------|
| `pnpm security:scan:quick` | Local — lockfiles + Trivy fs/config/secret (no image build) |
| `pnpm security:scan` | Local — full scan including Docker images + Grype |
| CI | [`.github/workflows/security.yml`](../.github/workflows/security.yml) on PR/push |

Reports land in `dist/security/report.md` (merged) with SARIF uploaded to GitHub Security.

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
