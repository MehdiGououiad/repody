# ADR 003: Modular platform modules

## Status

Accepted — 2026-06-14

## Decision

Platform workloads are grouped into **modules** that map to Kubernetes Deployments and optional local addons:

| Module | Kubernetes shape | Purpose |
|--------|------------------|---------|
| `control` | `repody-api` | API, dispatch, uploads |
| `workers` | `repody-worker-ocr`, `repody-worker-fast` | Hatchet worker pools |
| `edge` | `repody-web` | Next.js UI |
| `data` | Postgres, Redis, object storage | Durable state (bundled locally; external in production) |
| `queue` | Hatchet | Workflow engine (bundled locally; external in production) |
| `auth` | Keycloak | OIDC (bundled locally; external IdP in production) |
| `obs` | Grafana, Loki, Promtail | Logs (local addons) |
| `traces` | Tempo, OTEL | Traces (local addons) |
| `bugsink` | Bugsink | Error tracking (local addons) |

**Module catalog:** [deploy/platform-modules.mjs](../../deploy/platform-modules.mjs)

**Local CLI:** `deploy/scripts/k8s-local.mjs` via `pnpm k8s:local` (alias `pnpm dev`)

**Recipes:** `pnpm dev` · `pnpm stop` · `pnpm k8s:local:smoke`

Production entrypoint: Helm (`deploy/helm/repody`).

## Consequences

- One packaging path for local and production
- `pnpm deploy:check` validates Helm-oriented prerequisites
- Scale priority: worker pools → API → data plane → edge → external inference

## References

- [docs/PLATFORM.md](../PLATFORM.md)
- [docs/adr/004-cloud-kubernetes-packaging.md](./004-cloud-kubernetes-packaging.md)
- [docs/adr/005-kubernetes-only-external-inference.md](./005-kubernetes-only-external-inference.md)
