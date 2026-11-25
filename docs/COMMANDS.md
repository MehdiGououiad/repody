# Commands

Deploy follows **official upstream docs** - see [LOCAL.md](./LOCAL.md) (laptop) and [CLUSTER.md](./CLUSTER.md) (production).

## Develop (daily) - vendors / contributors (git checkout)

Build the images from this checkout (`repody-*:dev`, cached), start the platform, and (by default) **host NuExtract** (`repody:vlm`). To run a published release instead: `REPODY_BACKEND_IMAGE=… REPODY_WEB_IMAGE=… pnpm platform`.

| Command | When |
|---------|------|
| `pnpm platform setup` | **Once** - env files + build the images |
| `pnpm platform doctor` | **Preflight** - Node/pnpm, Docker, images, llama-server, NuExtract3 GGUFs, env, ports (also runs before start). Does **not** prove VRAM load or a full extract job. |
| `pnpm platform` | **Daily** - preflight + start stack + NuExtract on host |
| `pnpm platform -- --platform-only` | Containers only (no host models) |
| `pnpm platform -- --no-nuextract` | Skip NuExtract |
| `pnpm platform -- --no-build` | Start the images already built (skip the rebuild) |
| `pnpm platform status` | Health probes |
| `pnpm platform stop` | Tear down |
| `pnpm platform help` | Flags |
| `pnpm doctor` | Toolchain only (Node/pnpm) - prefer `pnpm platform doctor` |
| `pnpm db:migrate` | Apply Alembic migrations |

Guides: [LOCAL.md](./LOCAL.md) · [README.md](./README.md) (docs hub).

### Document models

| Catalog id | Process | Port | Notes |
|---|---|---|---|
| `repody:vlm` | NuExtract | `:8081` | **Default** with `pnpm platform` |

```bash
pnpm install
pnpm doctor
pnpm platform setup
pnpm platform                 # images from this checkout + host NuExtract
pnpm platform status
pnpm platform stop
```

> **Auth tip:** After Keycloak recreate, sign out and sign in again (or clear `localhost` cookies). Use **localhost**, not `127.0.0.1`.

### Contribute from source

Hub path above is the product runtime. For hacking API/UI from source:

| Command | When |
|---------|------|
| `pnpm platform dev` | Data plane + workers built from source; API (uvicorn) and UI (next dev) on the host with reload |
| `pnpm platform stop` | Stop host NuExtract and every container |
| `pnpm ui` | Next.js only (API already running) |

### Code quality

One gate covers both languages. See [CODE-QUALITY.md](./CODE-QUALITY.md) for
which tool owns which concern.

| Command | When |
|---------|------|
| `pnpm verify` | **Before pushing** - lint, format, types and dead code, both languages |
| `pnpm format` | Reformat everything in place (oxfmt + ruff); `bun fmt` is the frontend part |
| `pnpm lint:fix` / `pnpm lint:py:fix` | Apply the safe lint fixes |
| `bun lint` / `pnpm lint:py` | Lint and format check only (oxlint + oxfmt / ruff) |
| `bun check` / `pnpm typecheck:py` | TypeScript 7 `tsc --noEmit` / pyright |
| `bun test` | Frontend unit tests (`lib/`, `i18n/`) |
| `pnpm deadcode` | Unused files, exports and dependencies (knip; CI runs it). In a OneDrive folder it reports false positives: OneDrive turns folders into reparse points its file walker skips |
| `pnpm review:check` | `verify` + backend tests + deploy checks |

---

## OpenShift / client production

Deploy guide: [CLUSTER.md](./CLUSTER.md).

| Command | When |
|---------|------|
| `pnpm helm:lint` / `helm:template` | Chart checks |
| `pnpm deploy:check` | helm lint, helm template + kubeconform, kustomize, bake --print, docs links |
| `pnpm security:scan` | Trivy repository scan (lockfiles, secrets, misconfig) |

## Release / images

| Command | When |
|---------|------|
| `pnpm images:build` | Build locally (`docker buildx bake -f docker-bake.hcl --load`) |
| `pnpm images:release` | Build + push (`docker buildx bake -f docker-bake.hcl --push`; multi-arch via `REPODY_IMAGE_PLATFORMS`) |

Registry notes: [deploy/registry/README.md](../deploy/registry/README.md).

## Marketing site (repody.com)

A separate project in `site/` (own lockfile), a static export served by Cloudflare Workers.
Plan and structure: [docs/site/plan.md](site/plan.md).

| Command | When |
|---------|------|
| `pnpm --dir site install` | Once |
| `pnpm --dir site dev` | Local preview on http://localhost:3200 |
| `pnpm --dir site build` | Static export to `site/out/` |
| `pnpm --dir site run deploy` | Build and deploy by hand with Wrangler |

Pushes to `master` that touch the site deploy it through Cloudflare Workers Builds
(Worker `repody-site` > Settings > Builds); `.github/workflows/site.yml` only checks the build.

## Model serve (advanced / standalone)

Usually started by `pnpm platform`. Manual:

| Command | Port |
|---------|------|
| `pnpm llamacpp:serve` | `:8081` |

Stop: `pnpm llamacpp:stop`.

