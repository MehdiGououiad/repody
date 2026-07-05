# Deployment

**All guides:** [docs/deploy/README.md](./docs/deploy/README.md)

| Lane | Guide |
|------|--------|
| Local dev (Compose) | [docs/deploy/LOCAL.md](./docs/deploy/LOCAL.md) |
| Client OpenShift (bundled / external) | [docs/deploy/CLIENT.md](./docs/deploy/CLIENT.md) |
| Vendor release | [docs/deploy/RELEASE.md](./docs/deploy/RELEASE.md) |

## Vendor — push images

```powershell
$env:REPODY_IMAGE_REGISTRY="ghcr.io/yourorg/repody"
$env:REPODY_IMAGE_TAG="1.2.3"
pnpm images:release
```

Give clients: registry URL, immutable tag, Helm charts, and [docs/deploy/CLIENT.md](./docs/deploy/CLIENT.md).

## Client — four steps

1. Copy `deploy/client/values-external.example.yaml` (or bundled) to private GitOps repo
2. Apply namespace + ExternalSecrets ([docs/deploy/SECRETS.md](./docs/deploy/SECRETS.md))
3. `helm upgrade --install` or Argo CD ([docs/deploy/OPENSHIFT.md](./docs/deploy/OPENSHIFT.md) on OpenShift)
4. `curl https://api.<domain>/v1/healthz/live`

Preflight: `pnpm client:check` · `pnpm deploy:check`

Runtime secret keys: [deploy/ENV.md](./deploy/ENV.md)
