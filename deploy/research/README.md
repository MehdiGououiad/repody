# Research config (not product)

Kept for optional local model experiments wired into platform scripts.

| Dir | Used by |
|-----|---------|
| `qwen35/` | `pnpm qwen35:serve` · `deploy/scripts/research/qwen35-serve.mjs` |

Copy `paths.local.env.example` → `paths.local.env` (gitignored). Model weights and serve logs under `**/models/` and `**/logs/` are gitignored.
