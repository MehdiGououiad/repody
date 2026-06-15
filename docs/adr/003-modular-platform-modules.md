# ADR 003: Modular platform modules

## Status

Accepted — 2026-06-14

## Decision

**6 stack presets:** `dev`, `prod`, `prod-micro`, `vps`, `gpu`, `e2e`

**4 overlays** (flags): `--warmup`, `--lan`, `--public`, `--scale`

**7 modules:** `infra`, `control`, `workers`, `edge`, `obs`, `traces`, `bugsink`

**Single CLI:** `deploy/scripts/compose.mjs` via `pnpm compose`

**Recipes:** `pnpm dev` · `pnpm prod` · `pnpm stop`

Deploy scripts live under `deploy/scripts/`; VPS under `deploy/cloud/`.

## Consequences

- Fewer stack presets to sync and document
- `pnpm deploy:check` validates overlay combinations
- `deploy/compose/prod.yaml` uses YAML anchors for shared prod env
- `dev + --warmup` layers `warmup.yaml` on `dev.yaml` (does not replace dev overrides)
