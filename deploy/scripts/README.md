# Deploy scripts

Platform, Compose, release, and optional model-serve helpers.

See [docs/DEVELOPMENT.md](../../docs/DEVELOPMENT.md#scripts-map) for how this folder relates to `scripts/` and `backend/scripts/`.

| Area | Entry |
|------|--------|
| Daily Compose stack | `platform-dev.mjs` (`pnpm platform`) |
| Source contribute lane | `local-dev.mjs` (`pnpm dev:src:all`) |
| Images / supply chain | `../../docker-bake.hcl` (Buildx Bake), `release-supply-chain.mjs` |
| Host llama-server models (NuExtract, Qwen3.5, GLM-OCR) | `llama-serve.mjs <model>` (`pnpm llamacpp:serve`, `pnpm qwen35:serve`, `pnpm glmocr:serve`) |
