# ADR 004: Cloud and Kubernetes packaging

## Status

Accepted (2026-06-13)

## Context

The platform runs on Kubernetes (OpenShift, EKS/GKE/AKS, or generic), with independently scalable worker pools, and deploy boundaries that can evolve toward microservices without rewriting application code.

## Decisions

| Area                   | Decision                                                                                                      | Rationale                                                                              |
| ---------------------- | ------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| **Orchestrator**       | Kubernetes, Helm-first                                                                                        | Portable across clouds; HPA, ingress, secrets native                                   |
| **Local dev**          | Docker Compose (`pnpm platform`)                                                                              | Fast daily iteration                                                                   |
| **Production cluster** | Helm (+ optional Argo CD) on OpenShift / K8s                                                                  | Same charts clients receive - [CLUSTER.md](../CLUSTER.md)                              |
| **Data plane**         | External or operator-managed Postgres, Hatchet, and object storage by default                                 | Enterprise installs need independent lifecycle, backups, upgrades, and ownership       |
| **Queue**              | Hatchet (its Helm chart or Hatchet Cloud), [ADR 011](./011-hatchet.md)                                        | Timeouts, failure handling, per-client limits and cron in one engine                   |
| **Service split**      | Two release images: `repody-backend`, `repody-web`; backend runs API and worker roles via Kubernetes commands | Control / worker / edge scale independently without rebuilding duplicate Python images |
| **Inference**          | External vLLM (out of chart)                                                                                  | GPU workloads on separate node pool or managed inference                               |
| **Observability**      | Client-managed collectors; Bugsink via env DSN                                                                | Production observability is client-owned                                               |

## Escape hatches

- **No bundled data plane** (2026-11): the `repody-data` and `repody-auth` charts were removed; one app chart remains. Clients without managed services use operators (CloudNativePG examples in `deploy/managed/`).
- **Hatchet token**: `HATCHET_CLIENT_TOKEN` lives in the runtime Secret (ADR 011 replaced the Redis URL).
- **Edge**: Standard **Ingress** (`networking.k8s.io/v1`) on all platforms; optional OpenShift Routes or Gateway API

## Consequences

- Helm chart under `deploy/helm/repody/` is the production entrypoint.
- `pnpm images:release` produces and pushes the `repody-backend` and `repody-web` registry tags referenced in client values.
- Application code remains a monorepo; microservice boundaries are **deploy** boundaries, not separate repos yet.

## References

- [docs/CLUSTER.md](../CLUSTER.md)
- [CONTEXT.md](../../CONTEXT.md)
- [docs/adr/005-kubernetes-only-external-inference.md](./005-kubernetes-only-external-inference.md)
