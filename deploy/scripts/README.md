# Deploy scripts

Platform, Compose, release, and optional model-serve helpers.

See [docs/DEVELOPMENT.md](../../docs/DEVELOPMENT.md#scripts-map) for how this folder relates to `scripts/` and `backend/scripts/`.

| Area | Entry |
|------|--------|
| Daily Compose stack | `platform-dev.mjs` (`pnpm platform`) |
| Source contribute lane | `local-dev.mjs` (`pnpm dev:src:all`) |
| Images / supply chain | `build-images.mjs`, `release-supply-chain.mjs` |
| Qwen text model (OCR + Qwen paths) | `qwen35-serve.mjs` (`pnpm qwen35:serve`) |
