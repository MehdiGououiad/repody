# Platform Architecture

Repody deploys on **Kubernetes with Helm** in production (OpenShift client installs). **Local daily dev uses Docker Compose** — [docs/deploy/LOCAL.md](./deploy/LOCAL.md).

Command reference: [COMMANDS.md](./COMMANDS.md)

## Development vs production

| Path | When |
|------|------|
| Compose (`pnpm platform`) | Daily API/UI work, unit tests, migrations — [LOCAL.md](./deploy/LOCAL.md) |
| OpenShift / Kubernetes | Client production — [OPENSHIFT.md](./deploy/OPENSHIFT.md) |

## Production modules

| Module | Kubernetes shape | Purpose |
|--------|------------------|---------|
| control | `repody-api` Deployment | Workflows, runs, uploads, dispatch |
| workers | `repody-worker-extract`, `repody-worker-fast` | IDP capacity pools ([ADR 007](./adr/007-staged-agent-queues-taskiq.md)) |
| edge | `repody-web` Deployment | Next.js UI |
| data plane | Postgres, Redis, object storage | Durable platform state and Taskiq broker |
| auth | External OIDC provider | Authentication |
| inference | External OpenAI-compatible endpoint | Document-model VLM; not in the Repody chart |

Helm charts: `deploy/helm/repody-data`, `repody-auth`, `repody`.

## Client delivery

Vendor image artifacts:

- `repody-backend` for the API and worker roles.
- `repody-web` for Next.js.

Clients install with Helm or Argo CD — [docs/deploy/CLIENT.md](./deploy/CLIENT.md).

Release registry: GHCR or client container registry — [deploy/registry/README.md](../deploy/registry/README.md).

## Edge

**Standard Kubernetes Ingress** (`networking.k8s.io/v1`) everywhere — same manifests on OpenShift, EKS, GKE, on-prem. No chart OpenShift Route CRs.

Optional: Gateway API (Envoy) or OpenShift Routes for clients who prefer them (`gatewayApi.enabled` or `global.openshift.routes.enabled`).

## Observability

Client-managed OTEL and log stack — [docs/deploy/OBSERVABILITY.md](./deploy/OBSERVABILITY.md).
