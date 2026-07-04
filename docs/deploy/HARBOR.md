# Harbor (release registry)

Harbor is for **shipping images to clients**, not daily Compose dev.

**End-to-end vendor → client flow:** [VENDOR-TO-CLIENT.md](./VENDOR-TO-CLIENT.md)

Official install (v2.14):

1. [Download installer](https://goharbor.io/docs/2.14.0/install-config/download-installer/)
2. [Configure harbor.yml](https://goharbor.io/docs/2.14.0/install-config/configure-yml/)
3. [Run prepare](https://goharbor.io/docs/2.14.0/install-config/run-installer-script/)
4. [Start with Docker Compose](https://goharbor.io/docs/2.14.0/install-config/start-helm/)

## Quick path (manual)

```powershell
# 1. Download harbor-online-installer-v2.14.0.tgz from GitHub releases
# 2. Extract to a directory outside the repo (e.g. C:\harbor)
# 3. Copy deploy/harbor/harbor.yml.example → harbor/harbor.yml and edit hostname + admin password
# 4. In Git Bash from that directory:
./prepare
docker compose up -d
```

Template: [deploy/harbor/harbor.yml.example](../../deploy/harbor/harbor.yml.example)

## Release images

Registry base = **Harbor host + project** (`harbor.example.com/repody`). Images become `{registry}/repody-backend:{tag}`.

```powershell
$env:REPODY_IMAGE_REGISTRY="harbor.yourdomain.com/repody"
$env:REPODY_IMAGE_TAG="1.0.0"
docker login harbor.yourdomain.com
pnpm images:release
pnpm release:attest
pnpm release:promote -- --channel=staging
```

Harbor push/pull: [working with images](https://goharbor.io/docs/main/working-with-projects/working-with-images/pulling-pushing-images/)

Client pull secret and deploy: [VENDOR-TO-CLIENT.md](./VENDOR-TO-CLIENT.md) Part 2.

See [../../docs/deploy/RELEASE.md](../../docs/deploy/RELEASE.md) for SBOM, cosign, and promotion gates.

See [docs/COMMANDS.md](../../docs/COMMANDS.md) release lane.

## Troubleshooting download

If GitHub returns a small HTML file instead of the tarball, download manually in a browser or use a release mirror, then run `prepare` locally.
