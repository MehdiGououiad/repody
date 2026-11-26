# Commands

Every command runs from the repository root. CI's `deploy:check` fails when a `bun run`
command named in a doc, a script or a Compose file does not exist.

## Local platform

Guide: [LOCAL.md](./LOCAL.md).

| Command                   | What it does                                                                         |
| ------------------------- | ------------------------------------------------------------------------------------ |
| `bun run platform setup`  | Once: write the env files and build the images                                       |
| `bun run platform`        | Check the machine, build the images, start the stack and the host model              |
| `bun run platform dev`    | Data services in Compose; API and web app on the host, reloading on edits            |
| `bun run platform doctor` | Check Node, Bun, Docker, llama-server, the GGUF files, env files and ports           |
| `bun run platform status` | Health of each service                                                               |
| `bun run platform logs`   | Follow the API, web and worker logs                                                  |
| `bun run platform stop`   | Stop the host model and every container                                              |
| `bun run platform help`   | Commands and options (`--no-nuextract`, `--platform-only`, `--no-obs`, `--no-build`) |
| `bun run doctor`          | Check Node and Bun only                                                              |
| `bun run ui`              | The web app alone (`next dev`), with an API already running                          |
| `bun run db:migrate`      | Apply the Alembic migrations                                                         |
| `bun run db:reset`        | Drop every table, migrate and load the demo data (local only)                        |

## The local model (llama-server)

Guide: [deploy/llamacpp/README.md](../deploy/llamacpp/README.md). `bun run platform` starts and
stops it for you.

| Command                     | What it does                                  |
| --------------------------- | --------------------------------------------- |
| `bun run llamacpp:download` | Download the NuExtract3 GGUF files (`hf` CLI) |
| `bun run llamacpp:serve`    | Start llama-server on `:8081`                 |
| `bun run llamacpp:verify`   | Check it answers                              |
| `bun run llamacpp:stop`     | Stop it                                       |

## Before you push

Which tool owns which rule: [CODE-QUALITY.md](./CODE-QUALITY.md).

| Command                                    | What it does                                                          |
| ------------------------------------------ | --------------------------------------------------------------------- |
| `bun run verify`                           | Lint, format, types and dead code, both languages (what CI checks)    |
| `bun run review:check`                     | `verify`, the backend tests and the deploy checks                     |
| `bun lint` / `bun run lint:py`             | oxlint and oxfmt / ruff and import-linter                             |
| `bun run lint:fix` / `bun run lint:py:fix` | Apply the safe fixes                                                  |
| `bun run format`                           | Reformat everything (oxfmt and ruff); `bun fmt` is the frontend part  |
| `bun check` / `bun run typecheck:py`       | TypeScript (`tsc --noEmit`) / pyright                                 |
| `bun run deadcode`                         | Unused files, exports and dependencies (knip)                         |
| `bun run architecture:check`               | The backend's import layers (import-linter)                           |
| `bun run codegen:api`                      | Regenerate the OpenAPI document, its TypeScript types and the catalog |

In a OneDrive folder, `knip` can report false positives: OneDrive turns folders into reparse
points that its file walker skips.

## Tests

Details: [DEVELOPMENT.md](./DEVELOPMENT.md#tests).

| Command                    | What it runs                                             |
| -------------------------- | -------------------------------------------------------- |
| `bun test`                 | Frontend unit tests                                      |
| `bun run test:api`         | Backend unit and integration tests (needs Postgres)      |
| `bun run test:unit`        | Backend unit tests only                                  |
| `bun run test:integration` | Backend integration tests only                           |
| `bun run test:live`        | Backend tests against a running stack                    |
| `bun run test:e2e`         | Every Playwright spec against `bun run platform`         |
| `bun run test:e2e:smoke`   | Playwright: sign-in and navigation                       |
| `bun run test:platform`    | Playwright against a Compose stack (CI's `platform` job) |

## Images, deploy and security

| Command                                       | What it does                                                              |
| --------------------------------------------- | ------------------------------------------------------------------------- |
| `bun run images:build`                        | Build the images locally (`docker buildx bake -f docker-bake.hcl --load`) |
| `bun run images:release`                      | Build and push them (`REPODY_IMAGE_REGISTRY` and `REPODY_IMAGE_TAG`)      |
| `bun run deploy:check`                        | helm lint, kubeconform, Compose config, bake, the command checker         |
| `bun run helm:lint` / `bun run helm:template` | The Helm chart alone                                                      |
| `bun run security:scan`                       | Trivy on the repository (dependencies, secrets, misconfiguration)         |

The hosted demo is released with a git tag, not a command:
[deploy/vps/README.md](../deploy/vps/README.md#releasing).

## The marketing site

A separate project in `site/` with its own lockfile. Plan: [site/plan.md](./site/plan.md).

| Command                     | What it does                           |
| --------------------------- | -------------------------------------- |
| `bun install --cwd site`    | Once                                   |
| `bun run --cwd site dev`    | Preview on http://localhost:3200       |
| `bun run --cwd site build`  | Build                                  |
| `bun run --cwd site deploy` | Build and deploy by hand with Wrangler |

Pushes to `master` that touch `site/` deploy it through Cloudflare Workers Builds (Worker
`repody-site`); `.github/workflows/site.yml` checks the build.
