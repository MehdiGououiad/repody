# Commands

Deploy follows **official upstream docs** - see [LOCAL.md](./LOCAL.md) (laptop) and [CLUSTER.md](./CLUSTER.md) (production).

## Develop (daily) - vendors / contributors (git checkout)

Build the images from this checkout (`repody-*:dev`, cached), start the platform, and (by default) **host NuExtract** (`repody:vlm`). To run a published release instead: `REPODY_BACKEND_IMAGE=… REPODY_WEB_IMAGE=… bun run platform`.

| Command                               | When                                                                                                                                                               |
| ------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `bun run platform setup`              | **Once** - env files + build the images                                                                                                                            |
| `bun run platform doctor`             | **Preflight** - Node/Bun, Docker, images, llama-server, NuExtract3 GGUFs, env, ports (also runs before start). Does **not** prove VRAM load or a full extract job. |
| `bun run platform`                    | **Daily** - preflight + start stack + NuExtract on host                                                                                                            |
| `bun run platform -- --platform-only` | Containers only (no host models)                                                                                                                                   |
| `bun run platform -- --no-nuextract`  | Skip NuExtract                                                                                                                                                     |
| `bun run platform -- --no-build`      | Start the images already built (skip the rebuild)                                                                                                                  |
| `bun run platform status`             | Health probes                                                                                                                                                      |
| `bun run platform stop`               | Tear down                                                                                                                                                          |
| `bun run platform help`               | Flags                                                                                                                                                              |
| `bun run doctor`                      | Toolchain only (Node/Bun) - prefer `bun run platform doctor`                                                                                                       |
| `bun run db:migrate`                  | Apply Alembic migrations                                                                                                                                           |

Guides: [LOCAL.md](./LOCAL.md) · [README.md](./README.md) (docs hub).

### Document models

| Catalog id   | Process   | Port    | Notes                               |
| ------------ | --------- | ------- | ----------------------------------- |
| `repody:vlm` | NuExtract | `:8081` | **Default** with `bun run platform` |

```bash
bun install
bun run doctor
bun run platform setup
bun run platform                 # images from this checkout + host NuExtract
bun run platform status
bun run platform stop
```

> **Auth tip:** After Keycloak recreate, sign out and sign in again (or clear `localhost` cookies). Use **localhost**, not `127.0.0.1`.

### Contribute from source

Hub path above is the product runtime. For hacking API/UI from source:

| Command                 | When                                                                                            |
| ----------------------- | ----------------------------------------------------------------------------------------------- |
| `bun run platform dev`  | Data plane + workers built from source; API (uvicorn) and UI (next dev) on the host with reload |
| `bun run platform stop` | Stop host NuExtract and every container                                                         |
| `bun run ui`            | Next.js only (API already running)                                                              |

### Code quality

One gate covers both languages. See [CODE-QUALITY.md](./CODE-QUALITY.md) for
which tool owns which concern.

| Command                                    | When                                                                                                                                                                         |
| ------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `bun run verify`                           | **Before pushing** - lint, format, types and dead code, both languages                                                                                                       |
| `bun run format`                           | Reformat everything in place (oxfmt + ruff); `bun fmt` is the frontend part                                                                                                  |
| `bun run lint:fix` / `bun run lint:py:fix` | Apply the safe lint fixes                                                                                                                                                    |
| `bun lint` / `bun run lint:py`             | Lint and format check only (oxlint + oxfmt / ruff)                                                                                                                           |
| `bun check` / `bun run typecheck:py`       | TypeScript 7 `tsc --noEmit` / pyright                                                                                                                                        |
| `bun test`                                 | Frontend unit tests (`lib/`, `i18n/`)                                                                                                                                        |
| `bun run deadcode`                         | Unused files, exports and dependencies (knip; CI runs it). In a OneDrive folder it reports false positives: OneDrive turns folders into reparse points its file walker skips |
| `bun run review:check`                     | `verify` + backend tests + deploy checks                                                                                                                                     |

---

## OpenShift / client production

Deploy guide: [CLUSTER.md](./CLUSTER.md).

| Command                               | When                                                                        |
| ------------------------------------- | --------------------------------------------------------------------------- |
| `bun run helm:lint` / `helm:template` | Chart checks                                                                |
| `bun run deploy:check`                | helm lint, helm template + kubeconform, kustomize, bake --print, docs links |
| `bun run security:scan`               | Trivy repository scan (lockfiles, secrets, misconfig)                       |

## Release / images

| Command                  | When                                                                                                   |
| ------------------------ | ------------------------------------------------------------------------------------------------------ |
| `bun run images:build`   | Build locally (`docker buildx bake -f docker-bake.hcl --load`)                                         |
| `bun run images:release` | Build + push (`docker buildx bake -f docker-bake.hcl --push`; multi-arch via `REPODY_IMAGE_PLATFORMS`) |

Registry notes: [deploy/registry/README.md](../deploy/registry/README.md).

## Marketing site (repody.com)

A separate project in `site/` (own lockfile), a static export served by Cloudflare Workers.
Plan and structure: [docs/site/plan.md](site/plan.md).

| Command                         | When                                   |
| ------------------------------- | -------------------------------------- |
| `bun run --cwd site install`    | Once                                   |
| `bun run --cwd site dev`        | Local preview on http://localhost:3200 |
| `bun run --cwd site build`      | Static export to `site/out/`           |
| `bun run --cwd site run deploy` | Build and deploy by hand with Wrangler |

Pushes to `master` that touch the site deploy it through Cloudflare Workers Builds
(Worker `repody-site` > Settings > Builds); `.github/workflows/site.yml` only checks the build.

## Model serve (advanced / standalone)

Usually started by `bun run platform`. Manual:

| Command                  | Port    |
| ------------------------ | ------- |
| `bun run llamacpp:serve` | `:8081` |

Stop: `bun run llamacpp:stop`.
