# Documentation

**One place for all Repody docs.** Pick a lane below, then drill into topic pages.

---

## I want to…

| Goal | Start here |
|------|------------|
| **Run on a Mac (M1/M2/M3) end to end** | **[deploy/MAC.md](./deploy/MAC.md)** |
| Run on Windows / Linux laptop | [deploy/LOCAL.md](./deploy/LOCAL.md) |
| See every `pnpm` command | [COMMANDS.md](./COMMANDS.md) |
| Deploy to OpenShift / Kubernetes (client prod) | [deploy/OPENSHIFT.md](./deploy/OPENSHIFT.md) |
| Understand the product / architecture | [../CONTEXT.md](../CONTEXT.md) · [PLATFORM-INVENTORY.md](./PLATFORM-INVENTORY.md) |
| Publish images (Docker Hub / GHCR) | [../deploy/registry/README.md](../deploy/registry/README.md) · [deploy/RELEASE.md](./deploy/RELEASE.md) |

Root shortcuts: [../README.md](../README.md) · [../DEV.md](../DEV.md) · [../DEPLOY.md](../DEPLOY.md)

---

## Deploy (all lanes)

Canonical index: **[deploy/README.md](./deploy/README.md)**

| Path | Audience | Guide |
|------|----------|-------|
| **Mac laptop** | Apple Silicon from Hub images | [deploy/MAC.md](./deploy/MAC.md) |
| **Local** (Win / Mac / Linux) | Daily Compose platform | [deploy/LOCAL.md](./deploy/LOCAL.md) |
| **OpenShift / Kubernetes** | Client production | [deploy/OPENSHIFT.md](./deploy/OPENSHIFT.md) |
| Client profiles / Ingress | Integrators | [deploy/CLIENT.md](./deploy/CLIENT.md) |
| Secrets + hardening | Integrators | [deploy/SECRETS.md](./deploy/SECRETS.md) |
| Vendor → client handoff | Release managers | [deploy/VENDOR-TO-CLIENT.md](./deploy/VENDOR-TO-CLIENT.md) |
| Registry (Hub / GHCR / Harbor) | Release | [../deploy/registry/README.md](../deploy/registry/README.md) |
| Release / SBOM / cosign | Release | [deploy/RELEASE.md](./deploy/RELEASE.md) |
| Prod observability notes | Ops | [deploy/PROD-OBSERVABILITY.md](./deploy/PROD-OBSERVABILITY.md) · [deploy/OBSERVABILITY.md](./deploy/OBSERVABILITY.md) |

---

## Platform & engineering

| Topic | Doc |
|-------|-----|
| Full platform inventory | [PLATFORM-INVENTORY.md](./PLATFORM-INVENTORY.md) |
| Platform modules / Helm shape | [PLATFORM.md](./PLATFORM.md) |
| Backend layout | [BACKEND.md](./BACKEND.md) |
| Extraction overview | [EXTRACTION.md](./EXTRACTION.md) |
| External VLM contract | [REPODY-VLM.md](./REPODY-VLM.md) |
| PP-OCRv6 | [PADDLEOCR-V6.md](./PADDLEOCR-V6.md) |
| GLM-OCR | [GLM-OCR.md](./GLM-OCR.md) |
| Observability (logs / traces) | [OBSERVABILITY.md](./OBSERVABILITY.md) |
| Bugsink | [BUGSINK.md](./BUGSINK.md) |
| Testing pyramid | [TESTING.md](./TESTING.md) |
| E2E / live tests | [E2E.md](./E2E.md) |
| Benchmarks | [BENCHMARKING.md](./BENCHMARKING.md) |
| Code quality checklist | [CODE-QUALITY.md](./CODE-QUALITY.md) |
| Scripts ownership | [SCRIPTS.md](./SCRIPTS.md) |
| Pinned versions | [VERSIONS.md](./VERSIONS.md) |
| ADRs | [adr/README.md](./adr/README.md) |
| Diagrams (FR Mermaid) | [diagrams/README.md](./diagrams/README.md) |
| IDP functional design | [architecture/idp-functional-agents.md](./architecture/idp-functional-agents.md) |
| On-prem managed data | [ONPREM-MANAGED-DATA.md](./ONPREM-MANAGED-DATA.md) |
| Presentation notes | [PRESENTATION.md](./PRESENTATION.md) |

---

## Namespaces & local URLs

| Scope | Namespace | Notes |
|-------|-----------|-------|
| Compose laptop | (Docker) | API :8000 · UI :3000 · Keycloak :8080 |
| OpenShift / client | `repody` | API, web, workers (+ bundled data) |
| Optional CNPG | `repody-data` | Managed Postgres operator |

```powershell
kubectl -n repody logs -f deploy/repody-api
kubectl -n repody logs -l app.kubernetes.io/component=worker-extract --tail=200
```

| Path | URLs |
|------|------|
| Laptop Compose | http://localhost:3000 · http://localhost:8000 · http://localhost:8080 |
| Cluster | Ingress hosts from client values — [deploy/OPENSHIFT.md](./deploy/OPENSHIFT.md) |

---

## Repo layout (implementation)

| Path | Purpose |
|------|---------|
| [`deploy/`](../deploy/) | Helm, client kit, registry, scripts — [../deploy/README.md](../deploy/README.md) |
| `deploy/helm/repody/` | App chart (API, web, workers) |
| `deploy/helm/repody-data/` | Bundled Postgres / Redis / MinIO |
| `deploy/helm/repody-auth/` | Optional Keycloak |
| `deploy/client/` | Client values, secrets, Argo examples |
| `deploy/scripts/` | Platform, images, checks |
| `compose.portable.yaml` | Hub-image Compose overlay for `pnpm platform` |

Runtime env keys: [../deploy/ENV.md](../deploy/ENV.md) · host llama helpers: [../deploy/llamacpp/README.md](../deploy/llamacpp/README.md)

---

## Conventions

- **How-to** at repo root: `README.md`, `DEV.md`, `DEPLOY.md`, `CONTEXT.md`.
- **Topic references** in `docs/` (this tree).
- **Deploy how-tos** in `docs/deploy/`; **manifests/scripts** in `deploy/`.
- **Decisions** in `docs/adr/`, summarized in `CONTEXT.md`.
- Do not write platform logs into the workspace — use `kubectl`, Compose logs, or Grafana ([OBSERVABILITY.md](./OBSERVABILITY.md)).
