# Local Kubernetes

Runs Repody on kind with Envoy Gateway, Argo CD, and four namespaces:

| Namespace | Argo CD app | Contents |
|-----------|-------------|----------|
| `repody-data` | `repody-local-data` | PostgreSQL, Redis, MinIO |
| `repody-queue` | `repody-local-queue` | Hatchet stack |
| `repody-auth` | `repody-local-auth` | Keycloak |
| `repody-app` | `repody-local-app` | API, web, workers, Gateway routes |

Inference is external. Set `config.vllmBaseUrl` in `deploy/helm/repody/values-local.yaml`.

## Prerequisites

- Docker Desktop
- `kind`, `kubectl`, `helm`
- External OpenAI-compatible VLM endpoint
- Admin edit to hosts file
- GitHub access to the Repody GitOps repo. For private repos, sign in with your
  local Git credential manager before running `pnpm k8s:local`; the bootstrap
  registers that credential with Argo CD as a Kubernetes secret.

## Quick Start

```powershell
pnpm harbor:bootstrap       # once — local Harbor registry
pnpm k8s:local:hosts        # once — admin hosts file
pnpm k8s:local              # full stack (Argo CD; observability off by default)
pnpm k8s:local -- --with=obs   # add Grafana/Loki/Tempo/Bugsink
pnpm k8s:local -- --minimal   # faster: app + API + Keycloak only
pnpm k8s:local -- --minimal --logs   # minimal + tail api/worker logs after bootstrap
pnpm k8s:local:status
pnpm k8s:local:smoke
pnpm k8s:local:down
```

First cold start can take **15–25 minutes** (Harbor warm, image build, Helm subcharts, Postgres/Redis/MinIO/Hatchet/Keycloak). Re-runs with an existing cluster and cached Harbor images are much faster (often **3–8 minutes**). Use `--minimal` to skip Argo CD; add `--with=obs` only when you need Grafana/Bugsink locally.

Add to `C:\Windows\System32\drivers\etc\hosts`:

```text
127.0.0.1 app.repody.local api.repody.local files.repody.local auth.repody.local grafana.repody.local bugsink.repody.local
```

## URLs

| Service | URL |
|---------|-----|
| Web | http://app.repody.local |
| API | http://api.repody.local/v1/healthz/live |
| Keycloak | http://auth.repody.local |
| Argo CD (optional) | `pnpm argocd:port-forward` → https://127.0.0.1:8080 |
| Grafana | http://grafana.repody.local (`admin` / `audit`) |
| Bugsink | http://bugsink.repody.local (`admin@example.com` / `admin`) |

Sign in: `operator@repody.local` / `repody-dev`

## Smoke Test

`pnpm k8s:local:smoke` verifies the local Kubernetes wiring end to end:

- pods, Gateway, and HTTPRoutes
- web dashboard and Auth.js Keycloak redirect
- Keycloak password grant and authenticated API calls
- Postgres and Redis from the API pod
- MinIO presigned upload through `files.repody.local`
- Hatchet UI and worker connections
- Argo CD app presence (optional GitOps)
- Grafana, Loki, Promtail, Tempo, and Bugsink (when installed with `--with=obs`)

Argo CD is optional, installed from the upstream manifest, and accessed via
`pnpm argocd:port-forward` (not through the Repody Gateway). Observability addons
are in `local-addons-obs.yaml` (`--with=obs` only).

## Files

| File | Purpose |
|------|---------|
| `kind-repody-local.yaml` | kind cluster ports |
| `local-addons-obs.yaml` | Optional Grafana/Loki/Promtail/Tempo/Bugsink (`--with=obs`) |
| `../helm/repody/values-local.yaml` | App plane overrides (external data/queue/auth URLs) |
| `../argocd/repody-local-root.application.yaml` | Optional GitOps root for local Argo CD |
