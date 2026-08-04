# Commands

Deploy follows **official upstream docs** — see [docs/deploy/README.md](./deploy/README.md).

## Develop (daily) — same on Windows · macOS · Linux

Pull Hub images, start the platform, and (by default) host PP-OCR + Qwen.

| Command | When |
|---------|------|
| `pnpm platform setup` | **Once** — env files + pull Hub images |
| `pnpm platform` | **Daily** — start stack + PP-OCR + Qwen |
| `pnpm platform -- --with-nuextract` | Also start NuExtract (`:8081`) |
| `pnpm platform -- --platform-only` | Containers only (no host models) |
| `pnpm platform -- --with-glm` | Opt in GLM-OCR (`:8083`) |
| `pnpm platform -- --no-paddle` / `--no-qwen` | Skip a host model |
| `pnpm platform -- --no-pull` | Skip `docker pull` |
| `pnpm platform status` | Health probes |
| `pnpm platform stop` | Tear down |
| `pnpm platform doctor` | Prereqs |
| `pnpm platform help` | Flags |
| `pnpm models:warmup` | Re-warm PP-OCR + Qwen (+ NuExtract if configured) |
| `pnpm doctor` | Toolchain check |
| `pnpm db:migrate` | Apply Alembic migrations |

Aliases: `pnpm dev:all` → `platform up` · `pnpm dev:setup` / `dev:status` / `dev:stop` → same CLI.

Full guide: [deploy/LOCAL.md](./deploy/LOCAL.md).

### Document models

| Catalog id | Process | Port | Notes |
|---|---|---|---|
| `paddleocr:qwen` | PP-OCRv6 → Qwen | `:8868` + `:8084` | **Default** with `pnpm platform` |
| `paddleocr:v6` | PP-OCRv6 only | `:8868` | Markdown / OCR without Qwen |
| `repody:vlm` | NuExtract | `:8081` | `--with-nuextract` |
| `glm:ocr` | GLM-OCR | `:8083` | `--with-glm` (experimental) |

```bash
pnpm install
pnpm doctor
pnpm platform setup
pnpm platform
pnpm platform status
pnpm platform stop
```

> **Auth tip:** After Keycloak recreate, sign out and sign in again (or clear `localhost` cookies). Use **localhost**, not `127.0.0.1`.

### Contribute from source

Hub path above is the product runtime. For hacking API/UI from source:

| Command | When |
|---------|------|
| `pnpm dev:src:all` | Source-dev stack (local-dev) |
| `pnpm dev:app` | Foreground API + UI |
| `pnpm dev:api` | API only |
| `pnpm ui` | Next.js only |

---

## OpenShift / client

See [docs/deploy/OPENSHIFT.md](./deploy/OPENSHIFT.md).

| Command | When |
|---------|------|
| `pnpm openshift:client-test` | Full client-test profile |
| `pnpm openshift:client-ready` | Readiness gate |
| `pnpm prod:readiness` | Prod health check |
| `pnpm helm:lint` / `helm:template` | Chart checks |

## Release / images

| Command | When |
|---------|------|
| `pnpm images:build` | Build locally |
| `pnpm images:release` | Build + push (multi-arch via `REPODY_IMAGE_PLATFORMS`) |
| `pnpm release:all` | Push + attest + promote staging |

Registry notes: [deploy/registry/README.md](../deploy/registry/README.md).

## Model serve (advanced / standalone)

Usually started by `pnpm platform`. Manual:

| Command | Port |
|---------|------|
| `pnpm paddleocr:v6:serve` | `:8868` (auto-installs deps; starts Qwen companion by default) |
| `pnpm qwen35:serve` | `:8084` |
| `pnpm llamacpp:serve` | `:8081` |
| `pnpm glmocr:serve` | `:8083` |

Stop: `pnpm paddleocr:v6:stop` · `qwen35:stop` · `llamacpp:stop` · `glmocr:stop`.
