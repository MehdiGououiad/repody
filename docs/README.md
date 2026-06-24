# Documentation index

Repody runs on **Kubernetes** (local kind cluster or production cluster).

## Start here

| Doc | Audience | Contents |
|-----|----------|----------|
| [../README.md](../README.md) | Everyone | Product overview and quick start |
| [../DEV.md](../DEV.md) | Developers | Local kind + Helm workflow |
| [../DEPLOY.md](../DEPLOY.md) | Ops | Production Helm install |
| [../CONTEXT.md](../CONTEXT.md) | Tech leads | Architecture map and glossary |

## Operations

| Doc | Contents |
|-----|----------|
| [CLOUD-K8S.md](./CLOUD-K8S.md) | Helm values, secrets, Gateway API, scaling |
| [ONPREM-MANAGED-DATA.md](./ONPREM-MANAGED-DATA.md) | CloudNativePG, External Secrets, on-prem data plane |
| [AIRGAP.md](./AIRGAP.md) | Air-gapped image bundles and install |
| [../deploy/k8s/README.md](../deploy/k8s/README.md) | Local kind cluster (`pnpm k8s:local`) |
| [../deploy/ENV.md](../deploy/ENV.md) | Environment variables and secrets |
| [../deploy/argocd/README.md](../deploy/argocd/README.md) | GitOps with Argo CD |

## Platform features

| Doc | Contents |
|-----|----------|
| [PLATFORM.md](./PLATFORM.md) | Module layout (control, workers, edge, data plane) |
| [REPODY-VLM.md](./REPODY-VLM.md) | External document-model inference contract |
| [../deploy/llamacpp/README.md](../deploy/llamacpp/README.md) | llama-server for local NuExtract3 GGUF |
| [OBSERVABILITY.md](./OBSERVABILITY.md) | Logs, traces, Grafana |
| [BUGSINK.md](./BUGSINK.md) | Error tracking (Sentry-compatible) |
| [BENCHMARKING.md](./BENCHMARKING.md) | Performance benchmarks against live API |
| [E2E.md](./E2E.md) | Playwright + live pytest |

## Engineering

| Doc | Contents |
|-----|----------|
| [BACKEND.md](./BACKEND.md) | Backend layout and conventions |
| [BACKEND_STEPS.md](./BACKEND_STEPS.md) | Pointer to backend docs |
| [VERSIONS.md](./VERSIONS.md) | Pinned runtime versions |
| [adr/README.md](./adr/README.md) | Architecture decision records |

## Local URLs (after `pnpm k8s:local:hosts`)

| Service | URL |
|---------|-----|
| Web | http://app.repody.local |
| API | http://api.repody.local |
| Keycloak | http://auth.repody.local |
| Grafana | http://grafana.repody.local |
| Bugsink | http://bugsink.repody.local |
| Argo CD | http://argocd.repody.local |

Sign in: `operator@repody.local` / `repody-dev`
