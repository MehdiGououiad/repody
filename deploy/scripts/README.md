# Deploy scripts

The local platform CLI, the host llama-server, and the checks CI runs on deploy files.

See [docs/DEVELOPMENT.md](../../docs/DEVELOPMENT.md#scripts) for how this folder relates to `scripts/` and `backend/scripts/`.

| Area                        | Entry                                                                                          |
| --------------------------- | ---------------------------------------------------------------------------------------------- |
| Daily Compose stack         | `platform-dev.mjs` (`bun run platform`)                                                        |
| Develop from source         | `platform-dev.mjs` (`bun run platform dev`)                                                    |
| Images                      | `../../docker-bake.hcl` (Buildx Bake); signing and SBOM in `.github/workflows/images-ghcr.yml` |
| Deploy checks               | `deploy-check.mjs` (`bun run deploy:check`)                                                    |
| Commands named in the repo  | `check-command-docs.mjs` (run by `deploy:check`)                                               |
| Host NuExtract llama-server | `llama-serve.mjs` (`bun run llamacpp:serve`, `llamacpp:download`)                              |
| Shared helpers              | `runtime-env.mjs` (env files, Compose arguments, executables)                                  |
