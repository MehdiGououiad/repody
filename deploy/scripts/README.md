# Deploy scripts

Platform, Compose, release, and optional model-serve helpers.

See [docs/SCRIPTS.md](../../docs/SCRIPTS.md) for how this folder relates to `scripts/` and `backend/scripts/`.

| Area | Entry |
|------|--------|
| Daily Compose stack | `platform-dev.mjs` (`pnpm platform`) |
| Source contribute lane | `local-dev.mjs` (`pnpm dev:src:all`) |
| Images / supply chain | `build-images.mjs`, `release-supply-chain.mjs` |
| Research model serve | `research/` (Qwen 3.5) |
