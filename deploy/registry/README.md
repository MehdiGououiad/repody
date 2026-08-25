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
$env:REPODY_IMAGE_TAG="0.1.0"
$env:REPODY_IMAGE_PLATFORMS="linux/amd64,linux/arm64"
# Lean portable Hub image — no GLM-OCR torch stack.
# Local `pnpm platform -- --with-glm` builds a worker with otel,glmocr instead.
# To publish GLM-ready images: $env:REPODY_BACKEND_EXTRAS="otel,glmocr"
$env:REPODY_BACKEND_EXTRAS="otel"
pnpm images:release
```

Images:

- `mehdigououiad/repody-backend:0.1.0` (immutable tag; prefer digest in production GitOps)
- `mehdigououiad/repody-web:0.1.0` (immutable tag; prefer digest in production GitOps)

### Pull (any machine)

Public Hub images — no login required to pull:

```bash
docker pull mehdigououiad/repody-backend:0.1.0
docker pull mehdigououiad/repody-web:0.1.0
```

Docker picks `linux/arm64` on Apple Silicon and `linux/amd64` on Intel automatically.

Verify arches:

```bash
docker buildx imagetools inspect mehdigououiad/repody-backend:0.1.0
```

**Daily path** (pulls these for you): `pnpm platform` — see [docs/deploy/LOCAL.md](../../docs/deploy/LOCAL.md).

**Helm:** [deploy/client/values-dockerhub.example.yaml](../client/values-dockerhub.example.yaml).

**Portability boundary:** these images cover API, UI, and workers. Document-model
inference (NuExtract / PP-OCRv6 / Qwen / GLM-OCR) is **external** by design
([ADR 005](../../docs/adr/005-kubernetes-only-external-inference.md)). On a Mac
you still run or point at an inference endpoint separately — that is what makes
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

Helm values: [deploy/client/values-harbor.example.yaml](../client/values-harbor.example.yaml)

```bash
helm upgrade --install repody deploy/helm/repody -n repody \
  -f deploy/helm/repody/values.yaml \
  -f deploy/helm/repody/values-common.yaml \
  -f ~/repody-gitops/values.yaml \
  -f deploy/client/values-harbor.example.yaml \
  -f deploy/client/values-enterprise.example.yaml \
  --wait --timeout 25m
```

**TLS:** Production Harbor should use HTTPS. For HTTP-only registries, OpenShift must list the
host under `image.config.openshift.io/cluster` → `spec.registrySources.insecureRegistries`
([OKD docs](https://docs.okd.io/latest/openshift_images/image-configuration.html)). Prefer
HTTPS + `additionalTrustedCA` for self-signed CAs.

Full OpenShift order: [docs/deploy/OPENSHIFT.md](../../docs/deploy/OPENSHIFT.md#harbor-registry).

## Other OCI registries

ACR, ECR, GCR, GHCR, or self-hosted Distribution work the same way — set
`REPODY_IMAGE_REGISTRY`, push, create `registry-pull-secret`, point Helm `images.*`.

```powershell
$env:REPODY_IMAGE_REGISTRY="registry.example.com/repody"
$env:REPODY_IMAGE_TAG="<release>"
docker login registry.example.com
pnpm images:release
```

Image push commands fail unless `REPODY_IMAGE_REGISTRY` is set, so release images
cannot be pushed accidentally to an implicit registry namespace.

Then use [deploy/client/values-external.example.yaml](../client/values-external.example.yaml)
or [deploy/client/values-bundled.example.yaml](../client/values-bundled.example.yaml) as
the starting point for the client's GitOps values.

## Image Options

Default release images are intentionally small in number:

- `repody-backend` runs the API and worker roles.
- `repody-web` runs Next.js.

The backend image includes `otel` extras by default.
Built-in benchmark fixtures are excluded from release images unless
`REPODY_INCLUDE_BENCHMARK_FIXTURES=true`.

Build one image when iterating:

```powershell
pnpm images:build -- --only=backend
pnpm images:build -- --only=web
```

Use `pnpm images:push` only after `pnpm images:build` when you want to push an already-built registry-tagged image without rebuilding.
