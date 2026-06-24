# Local Kubernetes

Runs Repody on kind with Envoy Gateway, Argo CD, and in-cluster Keycloak.

Inference is external. The local Kubernetes stack does not pull or run a VLM model.
Set `config.vllmBaseUrl` in `deploy/helm/repody/values-local.yaml` or override it
when installing.

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
127.0.0.1 app.repody.local api.repody.local files.repody.local auth.repody.local argocd.repody.local grafana.repody.local bugsink.repody.local
```

## URLs

| Service | URL |
|---------|-----|
| Web | http://app.repody.local |
| API | http://api.repody.local/v1/healthz/live |
| Keycloak | http://auth.repody.local |
| Argo CD | http://argocd.repody.local (`admin` / password printed by `pnpm k8s:local`) |
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
- Argo CD app presence and Gateway UI
- Grafana, Loki, Promtail, Tempo, and Bugsink (when installed with `--with=obs`)

Local Kubernetes addons are split into `local-addons-gitops.yaml` (Argo CD route,
always applied with the full stack) and `local-addons-obs.yaml` (optional
observability, `--with=obs` only). They are intentionally separate from the Repody
app Helm chart. Production should point to external observability and error-tracking
services instead of bundling them in the app release.

## Files

| File | Purpose |
|------|---------|
| `kind-repody-local.yaml` | kind cluster ports |
| `local-addons-gitops.yaml` | Local-only Argo CD Gateway route |
| `local-addons-obs.yaml` | Optional Grafana/Loki/Promtail/Tempo/Bugsink (`--with=obs`) |
| `../helm/repody/values-local.yaml` | Single-replica + Gateway API hosts + external inference URL |
| `../argocd/repody-local.application.yaml` | Argo CD Application |
