# Platform Architecture

Repody deploys on **Kubernetes with Helm** in production (OpenShift client installs). **Local daily dev uses Docker Compose** — [docs/deploy/LOCAL.md](./deploy/LOCAL.md).

Command reference: [COMMANDS.md](./COMMANDS.md)

## Development paths

| Path | When |
|------|------|
| Compose (`pnpm dev`) | Daily API/UI work, unit tests, migrations |
| OpenShift CRC (`pnpm openshift:promote`) | Vendor cluster smoke — [docs/deploy/OPENSHIFT.md](./deploy/OPENSHIFT.md) |

## Production modules

| Module | Kubernetes shape | Purpose |
|--------|------------------|---------|
| control | `repody-api` Deployment | Workflows, runs, uploads, dispatch |
| workers | `repody-worker-ocr`, `repody-worker-fast` Deployments | Document extraction and fast validation |
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

Release registry: Harbor 2.14 — [docs/deploy/HARBOR.md](./deploy/HARBOR.md).

## Edge

**Standard Kubernetes Ingress** (`networking.k8s.io/v1`) everywhere — same manifests on OpenShift, EKS, GKE, on-prem. OpenShift overlay adds `route.openshift.io/termination` for edge TLS.

Optional: Gateway API (Envoy) or OpenShift Routes for clients who prefer them (`gatewayApi.enabled` or `global.openshift.routes.enabled`).

## Observability

Client-managed OTEL and log stack — [docs/deploy/OBSERVABILITY.md](./deploy/OBSERVABILITY.md).
