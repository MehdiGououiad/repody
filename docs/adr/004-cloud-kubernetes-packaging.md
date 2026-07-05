# ADR 004: Cloud and Kubernetes packaging

## Status

Accepted (2026-06-13)

## Context

The platform runs on Kubernetes (OpenShift, EKS/GKE/AKS, or generic), with independently scalable worker pools, and deploy boundaries that can evolve toward microservices without rewriting application code.

## Decisions

| Area | Decision | Rationale |
|------|----------|-----------|
| **Orchestrator** | Kubernetes, Helm-first | Portable across clouds; HPA, ingress, secrets native |
| **Local dev** | Docker Compose (`pnpm dev`) | Fast daily iteration |
| **Cluster validation** | OpenShift client test (`pnpm openshift:client-test`) | Same charts clients receive |
| **Data plane** | External or operator-managed Postgres, Redis/Valkey, and object storage by default | Enterprise installs need independent lifecycle, backups, upgrades, and ownership |
| **Bundled profile** | `repody-data` chart + `values-bundled.example.yaml` | Smaller tenants / air-gapped stacks |
| **Queue** | Taskiq over Redis Streams; Redis from `repody-data` or external | Reuses existing Redis; no separate workflow engine |
| **Service split** | Two release images: `repody-backend`, `repody-web`; backend runs API and worker roles via Kubernetes commands | Control / worker / edge scale independently without rebuilding duplicate Python images |
| **Inference** | External vLLM (out of chart) | GPU workloads on separate node pool or managed inference |
| **Observability** | Client-managed collectors; Bugsink via env DSN | Production observability is client-owned |

## Escape hatches

- **Bundled client data**: `deploy/client/values-bundled.example.yaml` enables in-cluster Postgres, Redis, MinIO via `repody-data`.
- **Redis URL**: production and bundled installs store `AUDIT_REDIS_URL` in the runtime Secret (Taskiq broker).
- **Edge**: Standard **Ingress** (`networking.k8s.io/v1`) on all platforms; optional OpenShift Routes or Gateway API

## Consequences

- Helm chart under `deploy/helm/repody/` is the production entrypoint.
- `pnpm images:release` produces and pushes the `repody-backend` and `repody-web` registry tags referenced in client values.
- Application code remains a monorepo; microservice boundaries are **deploy** boundaries, not separate repos yet.

## References

- [docs/deploy/CLIENT.md](../deploy/CLIENT.md)
- [docs/PLATFORM.md](../PLATFORM.md)
- [docs/adr/003-modular-platform-modules.md](./003-modular-platform-modules.md)
- [docs/adr/005-kubernetes-only-external-inference.md](./005-kubernetes-only-external-inference.md)
