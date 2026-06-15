# ADR 004: Cloud and Kubernetes packaging

## Status

Accepted (2026-06-13)

## Context

The platform needs to run beyond local Docker Compose: on Kubernetes (EKS/GKE/AKS or generic), with independently scalable worker pools, and a path toward true microservice deployment without rewriting application code.

## Decisions

| Area | Decision | Rationale |
|------|----------|-----------|
| **Orchestrator** | Kubernetes, Helm-first | Portable across clouds; HPA, ingress, secrets native |
| **Data plane** | In-cluster by default (Bitnami Postgres, Redis, MinIO) | Matches Compose topology; single `helm install` for small/medium clusters |
| **Hatchet** | Self-hosted Hatchet Lite + dedicated Postgres (in chart) | Same as Compose; no external SaaS dependency |
| **Service split** | Three images: `repody-api`, `repody-worker`, `repody-web` | Control / worker / edge scale independently; shared Python monorepo for now |
| **Inference** | External vLLM (out of chart) | GPU workloads on separate node pool or managed inference |
| **Observability** | Loki/Grafana optional (Compose); Bugsink via env DSN in K8s | Hybrid model from ADR observability work |
| **Compose path** | `deploy/compose/microservices.yaml` on prod stacks | Same images locally before K8s push |

## Escape hatches

- **Managed data**: set `postgresql.enabled=false`, `redis.enabled=false`, `minio.enabled=false` and populate `externalDatabase`, `externalRedis`, `externalObjectStorage`.
- **Hatchet token**: set `hatchet.clientToken` from Hatchet UI, or use bootstrap Job (`hatchet.bootstrapToken: true`).
- **Ingress**: `ingress.className` + TLS secret per cluster (nginx, ALB, traefik).

## Consequences

- Helm chart under `deploy/helm/repody/` is the production K8s entrypoint.
- `pnpm images:build` / `images:push` produce registry tags referenced in `values.yaml`.
- Application code remains a monorepo; microservice boundaries are **deploy** boundaries, not separate repos yet.
- Future: split Python packages, service mesh, KEDA queue-based autoscaling for workers.

## References

- [docs/CLOUD-K8S.md](../CLOUD-K8S.md)
- [docs/PLATFORM.md](../PLATFORM.md)
- [docs/adr/003-modular-platform-modules.md](./003-modular-platform-modules.md)
