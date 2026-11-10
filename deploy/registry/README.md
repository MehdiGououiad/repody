# Container Registry

Git stores desired Kubernetes state; the **registry** stores built images.

## Vendor To Client Model

| Role | Responsibility |
|------|----------------|
| **You (vendor)** | `pnpm images:release` to **your** GHCR or client registry |
| **Client** | Pull from your registry; deploy with **their** Argo CD or Helm |

Repody does not ship Argo CD for client production.

## Docker Hub (portable multi-arch)

Publish `linux/amd64` + `linux/arm64` (Apple Silicon Mac) platform images:

```powershell
docker login
$env:REPODY_IMAGE_REGISTRY="mehdigououiad"
$env:REPODY_IMAGE_TAG="1.0.0"
$env:REPODY_IMAGE_PLATFORMS="linux/amd64,linux/arm64"
pnpm images:release
```

Images:

- `mehdigououiad/repody-backend:1.0.0` (immutable tag; prefer digest in production GitOps)
- `mehdigououiad/repody-web:1.0.0` (immutable tag; prefer digest in production GitOps)

### Pull (any machine)

Public Hub images - no login required to pull:

```bash
docker pull mehdigououiad/repody-backend:1.0.0
docker pull mehdigououiad/repody-web:1.0.0
```

Docker picks `linux/arm64` on Apple Silicon and `linux/amd64` on Intel automatically.

Verify arches:

```bash
docker buildx imagetools inspect mehdigououiad/repody-backend:1.0.0
```

**Run a published release locally:** `REPODY_BACKEND_IMAGE=mehdigououiad/repody-backend:1.0.0 REPODY_WEB_IMAGE=mehdigououiad/repody-web:1.0.0 pnpm platform` (plain `pnpm platform` builds from the checkout) - see [docs/LOCAL.md](../../docs/LOCAL.md).

**Helm:** set `images.backend.repository` / `images.web.repository` to these names in your values.

**Portability boundary:** these images cover API, UI, and workers. Document-model
inference (NuExtract on llama-server) is **external** by design
([ADR 005](../../docs/adr/005-kubernetes-only-external-inference.md)). On a Mac
you still run or point at an inference endpoint separately - that is what makes
the platform portable across Windows, Linux, and macOS.

## GHCR

The `Publish images to GHCR` GitHub Actions workflow publishes:

- `ghcr.io/<owner>/repody-backend:<tag>` (API and worker roles)
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

Vendor push from a workstation:

```powershell
$env:REPODY_IMAGE_REGISTRY="ghcr.io/yourorg/repody"
$env:REPODY_IMAGE_TAG="<release>"
docker login ghcr.io
pnpm images:release
```

## Harbor (recommended on-prem registry)

Harbor is a CNCF graduated OCI registry. Clients commonly run it on OpenShift (Helm)
or as a standalone Docker Compose install.

Official docs:

- [Install Harbor](https://goharbor.io/docs/latest/install-config/)
- [Configure harbor.yml](https://goharbor.io/docs/latest/install-config/configure-yml-file/)
- [Harbor Helm](https://github.com/goharbor/harbor-helm)
- OpenShift pull secrets: [Using image pull secrets](https://docs.openshift.com/container_platform/latest/openshift_images/managing_images/using-image-pull-secrets.html)

### Vendor push

1. Client creates a Harbor project (example: `repody`) and a robot account with push/pull.
2. Vendor logs in and pushes an immutable tag:

```powershell
$env:REPODY_IMAGE_REGISTRY="harbor.example.com/repody"
$env:REPODY_IMAGE_TAG="1.0.0"
docker login harbor.example.com -u '<robot$repody+pusher>'
pnpm images:release
```

Images:

- `harbor.example.com/repody/repody-backend:1.0.0`
- `harbor.example.com/repody/repody-web:1.0.0`

### Client OpenShift pull

```bash
# Official OpenShift pull secret
oc -n repody create secret docker-registry registry-pull-secret \
  --docker-server=harbor.example.com \
  --docker-username='robot$repody+puller' \
  --docker-password='<token>' \
  --docker-email=unused@example.com

# Or via External Secrets — deploy/client/secrets/registry-pull.externalsecret.example.yaml
```

Helm values: point `images.*.repository` at `harbor.example.com/repody/repody-backend` (and `repody-web`) and add `imagePullSecrets: [{ name: registry-pull-secret }]`.

**TLS:** Production Harbor should use HTTPS. For HTTP-only registries, OpenShift must list the
host under `image.config.openshift.io/cluster` -> `spec.registrySources.insecureRegistries`
([OKD docs](https://docs.okd.io/latest/openshift_images/image-configuration.html)). Prefer
HTTPS + `additionalTrustedCA` for self-signed CAs.

Install order: [docs/CLUSTER.md](../../docs/CLUSTER.md#install).

## Other OCI registries

ACR, ECR, GCR, GHCR, or self-hosted Distribution work the same way - set
`REPODY_IMAGE_REGISTRY`, push, create `registry-pull-secret`, point Helm `images.*`.

```powershell
$env:REPODY_IMAGE_REGISTRY="registry.example.com/repody"
$env:REPODY_IMAGE_TAG="<release>"
docker login registry.example.com
pnpm images:release
```

Image push commands fail unless `REPODY_IMAGE_REGISTRY` is set, so release images
cannot be pushed accidentally to an implicit registry namespace.

Then start the client's GitOps values from
[values-production.yaml.example](../helm/repody/values-production.yaml.example).

## Image Options

Default release images are intentionally small in number:

- `repody-backend` runs the API and worker roles.
- `repody-web` runs Next.js.

The backend image includes `otel` extras by default.

Build one image when iterating:

```powershell
docker buildx bake -f docker-bake.hcl backend --load
docker buildx bake -f docker-bake.hcl web --load
```

`pnpm images:release` rebuilds from the build cache and pushes, so there is no separate push-only step.
