# Argo CD deployment

This directory contains GitOps entrypoints for Repody.

Argo CD owns the Repody Helm release only. Inference is external to this chart:
run **vLLM** or **llama-server** separately and set
`config.vllmBaseUrl` in the Repody values file.

Keep runtime secrets out of Git. Set `secrets.create=false` and
`secrets.existingSecret=repody-runtime-secrets`, then create that secret with
External Secrets, Sealed Secrets, SOPS, or a one-time cluster bootstrap.

Required keys in `repody-runtime-secrets`:

- `AUTH_SECRET`
- `AUTH_KEYCLOAK_CLIENT_SECRET`
- `AUDIT_DATABASE_URL`
- `AUDIT_REDIS_URL`
- `AUDIT_MINIO_ACCESS_KEY`
- `AUDIT_MINIO_SECRET_KEY`
- `HATCHET_CLIENT_TOKEN`

Optional keys:

- `AUDIT_VLLM_API_KEY`
- `BUGSINK_DSN`

## Local GitOps (`repody-local-*`)

Four Argo CD Applications (data → queue/auth → app) replace the monolithic `repody-local` app:

- `repody-local-data` — PostgreSQL, Redis, MinIO (`repody-data`)
- `repody-local-queue` — Hatchet (`repody-queue`)
- `repody-local-auth` — Keycloak (`repody-auth`)
- `repody-local-app` — API, web, workers, Gateway (`repody-app`)

Image tags for the app plane live in `deploy/helm/repody/values-local-images.yaml` (committed).
Harbor stores the images; Git records which tag should run; Argo CD reconciles.

```powershell
pnpm gitops:publish -- --all
```

Argo CD apps use automated sync/self-heal. **Synced** + revision =
cluster matches that Git commit.

## Staging Flow

```powershell
$env:REPODY_IMAGE_REGISTRY="harbor.yourdomain.com/repody"
$env:REPODY_IMAGE_TAG="$(git rev-parse --short=12 HEAD)"
pnpm images:build
pnpm images:push
pnpm deploy:staging
```

Or register Argo CD apps after pushing chart changes to Git:

```powershell
pnpm deploy:staging -- --argocd
kubectl apply -n argocd -f deploy/argocd/repody-staging.application.yaml
```

## Production Flow

Use CI to build and push immutable images, then let Argo CD deploy those tags.
Do not build images inside Argo CD.

```powershell
$env:REPODY_IMAGE_REGISTRY="harbor.yourdomain.com/repody"
$env:REPODY_IMAGE_TAG="$(git rev-parse --short=12 HEAD)"
pnpm images:build
pnpm images:push
```

Commit the same tag into the production values file:

```yaml
images:
  api:
    repository: harbor.yourdomain.com/repody/repody-api
    tag: "<git-sha>"
  worker:
    repository: harbor.yourdomain.com/repody/repody-worker
    tag: "<git-sha>"
  web:
    repository: harbor.yourdomain.com/repody/repody-web
    tag: "<git-sha>"

config:
  inferenceMode: vllm
  vllmBaseUrl: https://your-vlm-host/v1
  vllmServedModel: numind/NuExtract3
```

Then:

```powershell
kubectl apply -n argocd -f deploy/argocd/repody-project.yaml
kubectl apply -n argocd -f deploy/argocd/repody-production.application.yaml
```
