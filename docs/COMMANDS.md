# Commands

Deploy follows **official upstream docs** - see [LOCAL.md](./LOCAL.md) (laptop) and [CLUSTER.md](./CLUSTER.md) (production).

## Mac client (no source)

Pack from the private repo, ship the zip (not git):

| Command | When |
|---------|------|
| `pnpm client:pack:mac` | Build `dist/repody-mac-runtime-<tag>.zip` |

Client (on the Mac, after unzip): `./bin/repody setup` -> `./bin/repody start` - see [LOCAL.md - Mac runtime](./LOCAL.md#mac-runtime-no-source).

---

## Develop (daily) - vendors / contributors (git checkout)

Pull Hub images, start the platform, and (by default) **host NuExtract** (`repody:vlm`).

| Command | When |
|---------|------|
| `pnpm platform setup` | **Once** - env files + pull Hub images |
| `pnpm platform doctor` | **Preflight** - Node/pnpm, Docker, Hub images, llama-server, NuExtract3 GGUFs, env, ports (also runs before start). Does **not** prove VRAM load or a full extract job. |
| `pnpm platform` | **Daily** - preflight + start stack + NuExtract on host |
| `pnpm platform -- --platform-only` | Containers only (no host models) |
| `pnpm platform -- --no-nuextract` | Skip NuExtract |
| `pnpm platform -- --no-pull` | Skip `docker pull` |
| `pnpm platform status` | Health probes |
| `pnpm platform stop` | Tear down |
| `pnpm platform help` | Flags |
| `pnpm doctor` | Toolchain only (Node/pnpm) - prefer `pnpm platform doctor` |
| `pnpm db:migrate` | Apply Alembic migrations |

Guides: [LOCAL.md](./LOCAL.md) (Mac section + all OSes) · [README.md](./README.md) (docs hub).

### Document models

| Catalog id | Process | Port | Notes |
|---|---|---|---|
| `repody:vlm` | NuExtract | `:8081` | **Default** with `pnpm platform` |

```bash
pnpm install
pnpm doctor
pnpm platform setup
pnpm platform                 # Hub images + host NuExtract
pnpm platform status
pnpm platform stop
```

> **Auth tip:** After Keycloak recreate, sign out and sign in again (or clear `localhost` cookies). Use **localhost**, not `127.0.0.1`.

### Contribute from source

Hub path above is the product runtime. For hacking API/UI from source:

| Command | When |
|---------|------|
| `pnpm dev:src:setup` | Once - Compose data plane + migrations |
| `pnpm dev:src:all` | Source-dev stack (local-dev) + API + UI |
| `pnpm dev:src:app` | Foreground API + UI |
| `pnpm dev:src:api` | API only |
| `pnpm dev:src:status` | Health of the source lane |
| `pnpm dev:src:stop` | Stop host API/UI, host models and Compose |
| `pnpm ui` | Next.js only |

### Code quality

One gate covers both languages. See [CODE-QUALITY.md](./CODE-QUALITY.md) for
which tool owns which concern.

| Command | When |
|---------|------|
| `pnpm verify` | **Before pushing** - lint, format, types and dead code, both languages |
| `pnpm format` | Reformat everything in place (Biome + ruff) |
| `pnpm lint:fix` / `pnpm lint:py:fix` | Apply the safe lint fixes |
| `pnpm lint` / `pnpm lint:py` | Lint and format check only |
| `pnpm typecheck` / `pnpm typecheck:py` | `tsc --noEmit` / pyright |
| `pnpm deadcode` | Unused files, exports and dependencies (knip) |
| `pnpm review:check` | `verify` + backend tests + deploy checks |

---

## OpenShift / client production

Deploy guide: [CLUSTER.md](./CLUSTER.md).

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
| `pnpm images:build` | Build locally (`docker buildx bake --load`) |
| `pnpm images:release` | Build + push (`docker buildx bake --push`; multi-arch via `REPODY_IMAGE_PLATFORMS`) |
| `pnpm release:all` | Push + attest + promote staging |

Registry notes: [deploy/registry/README.md](../deploy/registry/README.md).

## Model serve (advanced / standalone)

Usually started by `pnpm platform`. Manual:

| Command | Port |
|---------|------|
| `pnpm llamacpp:serve` | `:8081` |

Stop: `pnpm llamacpp:stop`. Warm up: `pnpm llamacpp:warmup`.

## Architecture dossier

Source of truth: [ARCHITECTURE.md](./ARCHITECTURE.md). Diagram index: [diagrams/README.md](./diagrams/README.md).

`docs/ARCHITECTURE.docx` is generated, not edited by hand:

```bash
python docs/_md_to_docx.py
```
