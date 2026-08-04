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
# Lean portable image — no GLM-OCR torch stack (opt-in later if needed)
$env:REPODY_BACKEND_EXTRAS="otel"
pnpm images:release
```

Images:

- `mehdigououiad/repody-backend:0.1.0` (also `:latest`)
- `mehdigououiad/repody-web:0.1.0` (also `:latest`)

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

## On-prem / client registry

Use any OCI-compatible registry the client can reach (ACR, ECR, GCR, self-hosted Distribution, etc.).

```powershell
$env:REPODY_IMAGE_REGISTRY="registry.example.com/repody"
$env:REPODY_IMAGE_TAG="<release>"
docker login registry.example.com
pnpm images:release
```

Image push commands fail unless `REPODY_IMAGE_REGISTRY` is set, so release images
cannot be pushed accidentally to an implicit registry namespace.

The client creates a pull secret and points **their** Argo CD values at your registry:

```bash
kubectl -n repody create secret docker-registry registry-pull-secret \
  --docker-server=registry.example.com \
  --docker-username='<pull-user>' \
  --docker-password='<token>' \
  --docker-email=platform@example.com
```

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
