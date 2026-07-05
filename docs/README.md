# Documentation

Single map for all Repody docs. Start at the root guides, then drill into topic docs here.

## Start here

| Need | Doc |
|------|-----|
| **All commands** | [COMMANDS.md](./COMMANDS.md) |
| Product overview and quick start | [../README.md](../README.md) |
| Local development | [../DEV.md](../DEV.md) · [deploy/LOCAL.md](./deploy/LOCAL.md) |
| Production deployment | [deploy/README.md](./deploy/README.md) · [../DEPLOY.md](../DEPLOY.md) |
| **Client integration (their cluster)** | [deploy/CLIENT.md](./deploy/CLIENT.md) |
| **Secrets + hardening** | [deploy/SECRETS.md](./deploy/SECRETS.md) |
| **OpenShift (client + CRC lab)** | [deploy/OPENSHIFT.md](./deploy/OPENSHIFT.md) |
| Architecture context and glossary | [../CONTEXT.md](../CONTEXT.md) |
| Agent / Cursor workflow | [../AGENTS.md](../AGENTS.md) |

## Namespaces

| Scope | Namespace | Contents |
|-------|-----------|----------|
| Compose dev | (none — Docker) | API :8000, UI :3000, Keycloak :8080 |
| OpenShift / client | `repody` | API, web, workers; bundled data in same namespace |
| Optional CNPG | `repody-data` | Managed Postgres operator manifests |

**kubectl examples (OpenShift / client):**

```powershell
kubectl -n repody logs -f deploy/repody-api
kubectl -n repody logs -l app.kubernetes.io/component=worker-extract --tail=200
```

## Local URLs

| Path | URLs |
|------|------|
| Compose dev | API http://localhost:8000 · UI http://localhost:3000 · Keycloak http://localhost:8080 |
| OpenShift CRC | `*.apps-crc.testing` routes — [deploy/OPENSHIFT.md](./deploy/OPENSHIFT.md) |

## Operations

| Topic | Doc |
|-------|-----|
| Deploy guides (all lanes) | [deploy/README.md](./deploy/README.md) |
| Client production | [deploy/CLIENT.md](./deploy/CLIENT.md) |
| Prod observability | [deploy/PROD-OBSERVABILITY.md](./deploy/PROD-OBSERVABILITY.md) |
| On-prem managed data plane | [ONPREM-MANAGED-DATA.md](./ONPREM-MANAGED-DATA.md) |
| Air-gapped bundle and install | [AIRGAP.md](./AIRGAP.md) |
| Runtime env and secrets | [../deploy/ENV.md](../deploy/ENV.md) |
| Container registry (GHCR / on-prem) | [../deploy/registry/README.md](../deploy/registry/README.md) |
| Host llama-server helpers | [../deploy/llamacpp/README.md](../deploy/llamacpp/README.md) |
| External Secrets example | [../deploy/managed/external-secrets/README.md](../deploy/managed/external-secrets/README.md) |

## Engineering

| Topic | Doc |
|-------|-----|
| Backend layout and API inventory | [BACKEND.md](./BACKEND.md) |
| Code quality review checklist | [CODE-QUALITY.md](./CODE-QUALITY.md) |
| Platform modules and Helm shape | [PLATFORM.md](./PLATFORM.md) |
| External VLM contract | [REPODY-VLM.md](./REPODY-VLM.md) |
| Observability (logs, traces, Grafana) | [OBSERVABILITY.md](./OBSERVABILITY.md) |
| Error tracking (Bugsink) | [BUGSINK.md](./BUGSINK.md) |
| E2E and live tests | [E2E.md](./E2E.md) |
| Benchmarks | [BENCHMARKING.md](./BENCHMARKING.md) |
| Pinned runtime versions | [VERSIONS.md](./VERSIONS.md) |
| Architecture decisions | [adr/README.md](./adr/README.md) |

## Deploy directory

Implementation files live under [../deploy/](../deploy/). Read [../deploy/README.md](../deploy/README.md) for the layout.

| Path | Purpose |
|------|---------|
| `helm/repody/` | Application chart (API, web, Taskiq workers) |
| `helm/repody/values-common.yaml` | **Shared values layer** (local + production) |
| `helm/repody-data/` | Bundled data plane (Postgres, Redis, MinIO) |
| `helm/repody-auth/` | Optional Keycloak |
| `client/` | **Client integration kit** (values, secrets, Argo CD app) |
| `scripts/` | build, registry, Helm, OpenShift promote, smoke helpers |
| `managed/` | Optional production data-plane manifests |

## Conventions

- **How-to guides** live at the repo root: `README.md`, `DEV.md`, `DEPLOY.md`, `CONTEXT.md`.
- **Topic references** live in `docs/`.
- **Deploy implementation** lives in `deploy/` with short READMEs per subdirectory.
- **Decisions** are recorded in `docs/adr/` and summarized in `CONTEXT.md`.
- Do not write platform logs to workspace files - use `kubectl` or Grafana ([OBSERVABILITY.md](./OBSERVABILITY.md)).
