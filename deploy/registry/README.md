# Container Registry

Repody needs a container registry in addition to Git. GitHub/Argo CD stores the
desired Kubernetes state; the registry stores the built images that Kubernetes
pulls.

## Recommendation

- Use GHCR for SaaS, demos, staging, and the fastest release path.
- Use the client's registry for enterprise/on-prem installs.
- Deploy Harbor only when the client needs an on-prem registry and does not
  already operate one.

## GHCR

The `Publish images to GHCR` GitHub Actions workflow publishes:

- `ghcr.io/<owner>/repody-api:<tag>`
- `ghcr.io/<owner>/repody-worker:<tag>`
- `ghcr.io/<owner>/repody-web:<tag>`

It runs manually or when pushing `v*` tags, uses the repository `GITHUB_TOKEN`,
and uploads a Helm values artifact with the generated image coordinates.

For private GHCR packages, create a pull secret in the target namespace:

```bash
kubectl -n repody create secret docker-registry ghcr-pull-secret \
  --docker-server=ghcr.io \
  --docker-username=<github-user-or-bot> \
  --docker-password=<classic-pat-with-read:packages> \
  --docker-email=<email>
```

Then set:

```yaml
global:
  imagePullSecrets:
    - name: ghcr-pull-secret
```

## Harbor

Use Harbor when images must stay in the client's network or when they require
registry-native RBAC, replication, retention, vulnerability scanning, or
air-gapped import.

```bash
docker login harbor.example.com

REPODY_IMAGE_REGISTRY=harbor.example.com/repody \
REPODY_IMAGE_TAG=<git-sha-or-release> \
pnpm images:push
```

Create a Harbor robot account and Kubernetes pull secret:

```bash
kubectl -n repody create secret docker-registry harbor-pull-secret \
  --docker-server=harbor.example.com \
  --docker-username='robot$repody+pull' \
  --docker-password='<robot-token>' \
  --docker-email=platform@example.com
```

Then use `deploy/argocd/values-production.harbor.example.yaml` as the starting
point for the client's GitOps values.
