# Deploy scripts

Platform, Compose, release, and optional model-serve helpers.

See [docs/DEVELOPMENT.md](../../docs/DEVELOPMENT.md#scripts-map) for how this folder relates to `scripts/` and `backend/scripts/`.

| Area | Entry |
|------|--------|
| Daily Compose stack | `platform-dev.mjs` (`pnpm platform`) |
| Develop from source | `platform-dev.mjs` (`pnpm platform dev`) |
| Images | `../../docker-bake.hcl` (Buildx Bake); signing and SBOM in `.github/workflows/images-ghcr.yml` |
| Deploy checks | `deploy-check.mjs` (`pnpm deploy:check`) |
| Host NuExtract llama-server | `llama-serve.mjs` (`pnpm llamacpp:serve`) |
