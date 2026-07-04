# Harbor (release registry)

Use Harbor to **push images for clients**. Not required for Compose local dev.

Official documentation: [Harbor 2.14 install-config](https://goharbor.io/docs/2.14.0/install-config/)

## Install (manual — official steps)

1. [Download](https://goharbor.io/docs/2.14.0/install-config/download-installer/) `harbor-online-installer-v2.14.0.tgz`
2. Extract outside this repo (e.g. `C:\harbor`)
3. Copy [harbor.yml.example](./harbor.yml.example) → `harbor.yml` and set `hostname` + `harbor_admin_password`
4. Run `./prepare` then `docker compose up -d`

Full guide: [docs/deploy/HARBOR.md](../../docs/deploy/HARBOR.md)

## Push Repody images

```powershell
$env:REPODY_IMAGE_REGISTRY="harbor.yourdomain.com/repody"
$env:REPODY_IMAGE_TAG="1.0.0"
pnpm images:release
```

## Troubleshooting download
