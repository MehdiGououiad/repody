# Container Registry

Git stores desired Kubernetes state; the **registry** stores built images.

## Vendor To Client Model

| Role             | Responsibility                                                 |
| ---------------- | -------------------------------------------------------------- |
| **You (vendor)** | `bun run images:release` to **your** GHCR or client registry   |
| **Client**       | Pull from your registry; deploy with **their** Argo CD or Helm |

Repody does not ship Argo CD for client production.

## Where Repody's own images are

CI publishes three images to GHCR, `ghcr.io/mehdigououiad/repody-{backend,web,keycloak}`, and
signs each digest with cosign:

- every master commit whose tests pass, tagged with the commit (12 characters), which staging
  runs;
- every release tag `v1.2.3`, which promotes that commit's images by digest as `1.2.3`
  (`release.yml`): a release is never rebuilt.

The packages are private. Pull them after `docker login ghcr.io` with a token that has
`read:packages`. To run a release on a laptop:
`REPODY_BACKEND_IMAGE=ghcr.io/mehdigououiad/repody-backend:1.2.3 REPODY_WEB_IMAGE=ghcr.io/mehdigououiad/repody-web:1.2.3 bun run platform`
(plain `bun run platform` builds from the checkout, [docs/LOCAL.md](../../docs/LOCAL.md)).

The images hold the API, the worker (the same backend image), the web app and Keycloak. The
model is not in them: inference is an external endpoint by design
([ADR 005](../../docs/adr/005-kubernetes-only-external-inference.md)), such as the Modal app
([deploy/modal/README.md](../modal/README.md)).

## GHCR

Both workflows use the repository `GITHUB_TOKEN` and upload a Helm values artifact with the
image coordinates and digests. For private GHCR packages, create a pull secret in the target namespace:

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
bun run images:release
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
bun run images:release
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
bun run images:release
```

Image push commands fail unless `REPODY_IMAGE_REGISTRY` is set, so release images
cannot be pushed accidentally to an implicit registry namespace.

Then start the client's GitOps values from
[values-production.yaml.example](../helm/repody/values-production.yaml.example).

## Image Options

Default release images are intentionally small in number:

- `repody-backend` runs the API and worker roles.
- `repody-web` runs Next.js.
- `repody-keycloak` is Keycloak with Repody's realm built in.

The backend image includes `otel` extras by default.

Build one image when iterating:

```powershell
docker buildx bake -f docker-bake.hcl backend --load
docker buildx bake -f docker-bake.hcl web --load
```

`bun run images:release` rebuilds from the build cache and pushes, so there is no separate push-only step.
