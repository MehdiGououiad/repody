# ADR 003: Modular platform modules

## Status

Accepted — 2026-06-14

## Context

The monorepo runs as a single Docker Compose project with many overlay files (`compose.*.yaml`) and ad-hoc script combinations. Optional services (GlitchTip, Grafana/Loki) were started separately, which confused operators and blocked a clear path to horizontal scale and future Kubernetes extraction.

## Decision

Treat the runtime as **composable platform modules**, each mapping to one or more Compose services:

| Module | Services | Scale |
|--------|----------|-------|
| `infra` | postgres, redis, minio, hatchet-* | vertical |
| `control` | api | vertical (replicas later) |
| `workers` | worker, worker-fast | **horizontal** (`--scale`) |
| `edge` | web | vertical / CDN |
| `obs` | loki, grafana, promtail | optional addon |
| `traces` | tempo + OTEL | optional addon |
| `errors` | glitchtip + deps | optional addon |

**Stack presets** (`dev`, `dev-warm`, `prod`, `prod-scale`, `gpu`) select base compose overlays. **Addon modules** (`--with=obs,errors`) merge additional compose files and profiles.

Orchestration lives in `deploy/platform-modules.mjs` and `scripts/platform.mjs`. Legacy `scripts/docker.mjs` commands remain as aliases.

## Consequences

- One command can start warmup + logs + GlitchTip: `pnpm dev:warmup -- --logs --glitchtip`
- Scale workers without redeploying api: `pnpm platform:scale -- --stack=prod-scale --worker=3`
- Each module is a candidate **microservice / Helm chart** boundary for a later migration
- Compose files stay at repo root for now (no big-bang move); module manifest documents the seam

## Alternatives considered

- **Merge GlitchTip into `compose.yaml`** — rejected; couples lifecycle and RAM cost to every dev boot
- **Immediate K8s split** — rejected; Compose modules are the stepping stone
