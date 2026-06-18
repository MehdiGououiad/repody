# Local Kubernetes (prod path)

Runs Repody on **kind** with **Envoy Gateway** (Gateway API), **Argo CD**, and in-cluster **Keycloak**.

## Prerequisites

- Docker Desktop running **with Model Runner** (CPU inference via Repody VLM GGUF)
- `kind`, `kubectl`, `helm`
- Admin edit to hosts file (see below)

`pnpm k8s:local` runs `pnpm models:pull` so `repody/repody-vlm:q4_k_m-16k` is available in Model Runner.
Kind pods reach it at `http://model-runner.docker.internal/engines/llama.cpp/v1` (Docker Desktop DNS).

## Quick start

```powershell
pnpm k8s:local          # create cluster + deploy
pnpm k8s:local:status   # pods / routes / Argo CD apps
pnpm k8s:local:down     # delete kind cluster
```

Add to `C:\Windows\System32\drivers\etc\hosts`:

```
127.0.0.1 app.repody.local api.repody.local files.repody.local auth.repody.local
```

## URLs

| Service | URL |
|---------|-----|
| Web | http://app.repody.local |
| API | http://api.repody.local/v1/healthz/live |
| Keycloak | http://auth.repody.local |
| Argo CD | `kubectl port-forward svc/argocd-server -n argocd 8080:443` → https://localhost:8080 |

Sign in: `operator@repody.local` / `repody-dev`

## GitOps note

Bootstrap installs via **local Helm** with images published to **`localhost:5001`** (same pull model as Harbor on client clusters) and an **immutable git-SHA tag**. Argo CD app `repody-local` is registered for manual sync after `git push`, or:

```bash
argocd login localhost:8080 --insecure
argocd app sync repody-local --local deploy/helm/repody
```

## Files

| File | Purpose |
|------|---------|
| `kind-repody-local.yaml` | kind cluster (ports 80/443) |
| `keycloak.yaml` | Legacy reference; local bootstrap uses Helm `keycloak.enabled` |
| `../helm/inference-llamacpp/` | CPU staging inference (llama.cpp server; not vLLM) |
| `../helm/repody/values-local.yaml` | Single-replica + Gateway API hosts |
| `../argocd/repody-local.application.yaml` | Argo CD Application |
