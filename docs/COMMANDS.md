# Commands

Deploy follows **official upstream docs** — see [docs/deploy/README.md](./deploy/README.md).

## Develop (daily) — same on Windows · macOS · Linux

Pull Hub images, start the platform, and (by default) **host NuExtract** (`repody:vlm`).

| Command | When |
|---------|------|
| `pnpm platform setup` | **Once** — env files + pull Hub images |
| `pnpm platform doctor` | **Preflight** — Node/pnpm, Docker, Hub images, llama-server, NuExtract3 GGUFs, env, ports (also runs before start). Does **not** prove VRAM load or a full extract job. |
| `pnpm platform` | **Daily** — preflight + start stack + NuExtract on host |
| `pnpm platform -- --with-paddle` | Also PP-OCR + Qwen (`paddleocr:qwen`) |
| `pnpm platform -- --platform-only` | Containers only (no host models) |
| `pnpm platform -- --with-glm` | GLM-OCR host + local extract worker with official SDK |
| `pnpm platform -- --no-nuextract` | Skip NuExtract |
| `pnpm platform -- --no-pull` | Skip `docker pull` |
| `pnpm platform status` | Health probes |
| `pnpm platform stop` | Tear down |
| `pnpm platform help` | Flags |
| `pnpm models:warmup` | Re-warm configured host models |
| `pnpm doctor` | Toolchain only (Node/pnpm) — prefer `pnpm platform doctor` |
| `pnpm db:migrate` | Apply Alembic migrations |

Aliases: `pnpm dev:all` → `platform up` · `pnpm dev:setup` / `dev:status` / `dev:stop` → same CLI.

Guides: [deploy/MAC.md](./deploy/MAC.md) (Apple Silicon) · [deploy/LOCAL.md](./deploy/LOCAL.md) (all OSes) · [README.md](./README.md) (docs hub).

### Document models

| Catalog id | Process | Port | Notes |
|---|---|---|---|
| `repody:vlm` | NuExtract | `:8081` | **Default** with `pnpm platform` |
| `paddleocr:qwen` | PP-OCRv6 → Qwen JSON | `:8868` + `:8084` | `--with-paddle` |
| `glm:qwen` | GLM-OCR SDK → Qwen JSON | `:8083` + `:8084` | `--with-glm` (builds local worker with SDK) |

```bash
pnpm install
pnpm doctor
pnpm platform setup
pnpm platform -- --with-paddle --with-glm   # NuExtract + paddle + GLM
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

### Code quality

One gate covers both languages. See [CODE-QUALITY.md](./CODE-QUALITY.md) for
which tool owns which concern.

| Command | When |
|---------|------|
| `pnpm verify` | **Before pushing** — lint, format, types and dead code, both languages |
| `pnpm format` | Reformat everything in place (Biome + ruff) |
| `pnpm lint:fix` / `pnpm lint:py:fix` | Apply the safe lint fixes |
| `pnpm lint` / `pnpm lint:py` | Lint and format check only |
| `pnpm typecheck` / `pnpm typecheck:py` | `tsc --noEmit` / pyright |
| `pnpm deadcode` | Unused files, exports and dependencies (knip) |
| `pnpm review:check` | `verify` + backend tests + deploy checks |

---

## OpenShift / client production

Deploy guide: [docs/deploy/OPENSHIFT.md](./deploy/OPENSHIFT.md).

| Command | When |
|---------|------|
| `pnpm helm:deps:update` | Refresh chart dependencies before install |
| `pnpm helm:lint` / `helm:template` | Chart checks |
| `pnpm client:check` | Client Helm / ESO preflight |
| `pnpm deploy:check` | Deploy contract checks |
| `pnpm prod:readiness` | Live API readiness against a cluster URL |

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
