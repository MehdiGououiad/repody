# ADR 004: Cloud and Kubernetes packaging

## Status

Accepted (2026-06-13)

## Context

The platform runs on Kubernetes (EKS/GKE/AKS or generic), with independently scalable worker pools, and deploy boundaries that can evolve toward microservices without rewriting application code.

## Decisions

| Area | Decision | Rationale |
|------|----------|-----------|
| **Orchestrator** | Kubernetes, Helm-first | Portable across clouds; HPA, ingress, secrets native |
| **Local dev** | kind + same Helm chart (`values-local.yaml`) | Parity with production packaging |
| **Data plane** | External or operator-managed Postgres, Redis/Valkey, and object storage by default | Enterprise installs need independent lifecycle, backups, upgrades, and ownership |
| **Hatchet** | External Hatchet endpoint by default; Hatchet Lite only for local testing | Avoids embedding development queue infrastructure in client production clusters |
| **Service split** | Three images: `repody-api`, `repody-worker`, `repody-web` | Control / worker / edge scale independently; shared Python monorepo for now |
| **Inference** | External vLLM (out of chart) | GPU workloads on separate node pool or managed inference |
| **Observability** | Loki/Grafana/Tempo via local addons; production via cluster collectors; Bugsink via env DSN | Hybrid model from observability work |

## Escape hatches

- **Bundled local data**: `values-local.yaml` explicitly enables bundled Postgres, Redis, MinIO, Keycloak, and Hatchet Lite for kind/local testing only.
- **Hatchet token**: production sets `externalHatchet.*` and stores `HATCHET_CLIENT_TOKEN` in the runtime Secret.
- **Ingress**: `ingress.className` + TLS secret per cluster (nginx, ALB, traefik, Gateway API).

## Consequences

- Helm chart under `deploy/helm/repody/` is the production and local K8s entrypoint.
- `pnpm images:build` / `images:push` produce registry tags referenced in `values.yaml`.
- Application code remains a monorepo; microservice boundaries are **deploy** boundaries, not separate repos yet.
- Future: split Python packages, service mesh, KEDA queue-based autoscaling for workers.

## References

- [docs/CLOUD-K8S.md](../CLOUD-K8S.md)
- [docs/PLATFORM.md](../PLATFORM.md)
- [docs/adr/003-modular-platform-modules.md](./003-modular-platform-modules.md)
- [docs/adr/005-kubernetes-only-external-inference.md](./005-kubernetes-only-external-inference.md)
