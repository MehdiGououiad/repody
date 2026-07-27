# Commands

Deploy follows **official upstream docs** — see [docs/deploy/README.md](./deploy/README.md).

## Develop (daily)

| Command | When |
|---------|------|
| `pnpm dev:setup` | **Once** — copy env files, start Compose, migrate |
| `pnpm dev:all` | **Daily** — Compose + **all three models** + observability + API + UI |
| `pnpm dev:all:no-glmocr` | Same, skip GLM-OCR (`:8083`) — less VRAM |
| `pnpm dev:all:no-nuextract` | Same, skip NuExtract (`:8081`) — less VRAM |
| `pnpm dev:all:paddle-only` | Skip NuExtract + GLM — PP-OCRv6 only |
| `pnpm models:warmup` | After start — force-warm NuExtract + PP-OCRv6 + GLM-OCR |
| `pnpm dev:status` | Health probes (API, UI, NuExtract, PP-OCRv6, GLM-OCR, obs) |
| `pnpm dev:stop` | Stop API, UI, all three models, and Compose |
| `pnpm dev:restart` | Restart all three models + workers (e.g. after GPU reset) |
| `pnpm db:migrate` | Apply Alembic migrations |
| `pnpm doctor` | Toolchain check |

Split logs (optional):

| Command | When |
|---------|------|
| `pnpm dev` | Background stack only (Compose + workers + models), then exit |
| `pnpm dev:app` | Foreground API + UI (stack already running) |

### All three document models

| Catalog id | Process | Port | Serve / warm |
|---|---|---|---|
| `repody:vlm` | NuExtract (llama-server) | `:8081` | `pnpm llamacpp:serve` · `pnpm llamacpp:warmup` |
| `paddleocr:v6` | PP-OCRv6 (PaddleX `/ocr`) | `:8868` | `pnpm paddleocr:v6:serve` · `pnpm paddleocr:v6:warmup` |
| `glm:ocr` | GLM-OCR (llama-server) | `:8083` | `pnpm glmocr:serve` · `pnpm glmocr:warmup` |

`pnpm dev:all` starts **all three** (plus Grafana/Loki/Tempo/Bugsink). First serve also warms each model; use `pnpm models:warmup` to re-prime.

```powershell
# First time
pnpm install
pnpm doctor
pnpm dev:setup
# NuExtract: copy deploy/llamacpp/paths.local.env.example → paths.local.env
# GLM (optional local GGUF): copy deploy/glmocr/paths.local.env.example → paths.local.env
# PP-OCRv6 once: pnpm paddleocr:v6:install

# Daily — everything
pnpm dev:all
pnpm models:warmup          # optional if first serve already warmed
pnpm dev:status

# Stop
pnpm dev:stop
```

Skip one model (VRAM / iGPU) — prefer the named scripts (no `--` needed):

```powershell
pnpm dev:all:no-glmocr          # skip GLM-OCR :8083
pnpm dev:all:no-nuextract       # skip NuExtract :8081
pnpm dev:all:paddle-only        # PP-OCRv6 only
pnpm dev:all -- --no-paddleocr  # skip PP-OCRv6 :8868
pnpm dev:all -- --no-obs        # skip observability
```

Aliases: `--no-nuextract` = `--no-llama` = `--no-vlm` · `--no-glmocr` = `--no-glm`

> **Auth tip:** After `pnpm dev:reset` / Keycloak recreate, sign out and sign in again (or clear `localhost` cookies). Old JWTs fail with `Unable to find a signing key that matches: "…"`.

Or disable in `backend/.env`: `AUDIT_REPODY_VLM_ENABLED`, `AUDIT_PADDLEOCR_V6_ENABLED`, `AUDIT_GLM_OCR_ENABLED`.

> **Note:** NuExtract and GLM both use llama-server. On shared iGPU / low RAM, Next.js can crash with Windows `0xC0000409` / exit `3221226505`. Prefer `pnpm dev:all:no-glmocr` or `pnpm dev:all:no-nuextract` (or `pnpm dev:all:paddle-only`). If the UI dies, API/models often keep running — use `pnpm ui` or `pnpm dev:app` to bring the UI back.

Model docs: [REPODY-VLM.md](./REPODY-VLM.md) · [PADDLEOCR-V6.md](./PADDLEOCR-V6.md) · [GLM-OCR.md](./GLM-OCR.md)

### Granular (optional)

| Command | When |
|---------|------|
| `pnpm dev:api` | FastAPI only |
| `pnpm ui` | Next.js only (:3000) |
| `pnpm dev:worker` | Both Taskiq worker pools (Docker) |
| `pnpm llamacpp:serve` / `:stop` / `:verify` / `:warmup` | NuExtract alone |
| `pnpm paddleocr:v6:install` / `:serve` / `:stop` / `:verify` / `:warmup` | PP-OCRv6 alone |
| `pnpm glmocr:serve` / `:stop` / `:verify` / `:warmup` / `:download` | GLM-OCR alone |
| `pnpm db:reset` | Drop schema, migrate, re-seed |
| `pnpm dev:reset` | Wipe Compose volumes + DB + rebuild workers |
| `pnpm test:api` | Backend tests |
| `pnpm lint` / `pnpm typecheck` | Frontend quality |

## OpenShift client test

[docs/deploy/OPENSHIFT.md](./deploy/OPENSHIFT.md) · Production client: [docs/deploy/CLIENT.md](./deploy/CLIENT.md)

Requires `kubectl` + `helm` + `docker` logged in to an OpenShift cluster (kubeconfig).

| Command | When |
|---------|------|
| `pnpm openshift:infra` | **Once** — Harbor, Vault, ESO, OTEL, Argo CD |
| `pnpm openshift:e2e` | **Repeat** — build → push → seed → sync → verify → logs |
| `pnpm openshift:client-test` | Full run: infra + e2e (GitOps default; add `--clean` to reset) |
| `pnpm openshift:client-test:external` | External profile |
| `pnpm openshift:client-test:helm` | Direct Helm instead of Argo CD |
| `pnpm openshift:preflight` | Check kubectl, helm, docker |
| `pnpm openshift:client-ready` | Production-shaped validation on running lab |

Flags: `--registry=harbor|openshift` · `--helm` · `--clean` · `--skip-images` · `--skip-build` · `--vlm`

```powershell
pnpm openshift:infra
pnpm openshift:e2e --skip-build
```

## Release (vendor → client)

[docs/deploy/VENDOR-TO-CLIENT.md](./deploy/VENDOR-TO-CLIENT.md) · [docs/deploy/RELEASE.md](./deploy/RELEASE.md)

```powershell
$env:REPODY_IMAGE_REGISTRY="ghcr.io/yourorg/repody"
$env:REPODY_IMAGE_TAG="1.2.3"
docker login ghcr.io
pnpm images:release
pnpm release:attest
pnpm release:promote -- --channel=staging
```

## Security scanning

| Command | When |
|---------|------|
| `pnpm security:scan:quick` | Lockfiles + Trivy fs/config/secret |
| `pnpm security:scan` | Full scan including Docker images + Grype |

## Helm / client

| Command | When |
|---------|------|
| `pnpm helm:deps:update` / `:check` / `pnpm helm:lint` / `pnpm helm:template` | Charts |
| `pnpm client:check` / `pnpm deploy:check` / `pnpm enterprise:secrets` | Client contracts |

## Tests

| Command | When |
|---------|------|
| `pnpm test:unit` | Fast pure backend tests |
| `pnpm test:integration` | ASGI + Postgres |
| `pnpm test:api` | Unit + integration (CI default) |
| `pnpm test:live` | Live API (stack required) |
| `pnpm test:e2e` | Playwright UI |
| `pnpm test:platform:report` | Markdown/HTML under `reports/platform-tests/` |

Details: [docs/TESTING.md](./TESTING.md).

Production namespace: `repody`. Local Compose uses localhost ports.
