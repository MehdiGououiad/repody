# Deployment guide

Stack SSOT: [`deploy/platform-modules.mjs`](./deploy/platform-modules.mjs) · CLI: [`deploy/scripts/compose.mjs`](./deploy/scripts/compose.mjs) · Index: [`deploy/README.md`](./deploy/README.md)

```bash
pnpm compose help
pnpm compose stacks      # dev, prod, prod-micro, vps, gpu, e2e
pnpm deploy:check        # CI validation
```

## Command reference

| Goal | Command |
|------|---------|
| **Ubuntu VPS** | `bash deploy/cloud/deploy.sh` |
| Local production | `pnpm compose up --stack=prod --build` |
| GPU / vLLM | `pnpm compose up --stack=gpu --build` |
| Office LAN | `pnpm configure:lan` then `pnpm compose up --stack=prod --lan --build` |
| Public HTTPS | `pnpm compose up --stack=prod --public --build` |
| VPS-equivalent local | `pnpm compose up --stack=vps --build` |
| Scale workers | `pnpm compose up --stack=prod --scale --scale-worker=2 --build` |
| Observability | `pnpm compose up --stack=prod --with=obs,traces --build` |
| Air-gap bundle | `pnpm airgap:build -- --version X.Y.Z` — [docs/AIRGAP.md](./docs/AIRGAP.md) |
| VPS + observability | `pnpm compose up --stack=vps --with=obs,traces --build` |
| Warmup overlay | `pnpm compose up --stack=prod --warmup --build --wait` |
| Kubernetes images | `pnpm images:build` → [docs/CLOUD-K8S.md](./docs/CLOUD-K8S.md) |

### Stacks and overlays

| Stack | Use |
|-------|-----|
| `dev` | Local backend development |
| `prod` | Single-host production |
| `prod-micro` | Per-role image tags (CI / K8s) |
| `vps` | Ubuntu VPS file chain |
| `gpu` | vLLM on same machine |
| `e2e` | Playwright smoke |

**Overlays** (combine with `--stack`): `--warmup` `--lan` `--public` `--scale`  
**Modules** (optional): `--with=obs,traces,bugsink`

---

## Ubuntu VPS

**First install:** `bash deploy/cloud/deploy.sh`  
**Updates:** `git pull && bash deploy/cloud/bootstrap.sh` (add `REPODY_BUILD=1` after code changes)  
**Secrets:** `bash deploy/cloud/setup-env.sh` (interactive; see [deploy/ENV.md](./deploy/ENV.md))

---

## Local production

```powershell
pnpm compose up --stack=prod --build
```

GPU: `pnpm verify:gpu` then `pnpm compose up --stack=gpu --build`

### LAN sharing

```powershell
pnpm configure:lan
pnpm compose up --stack=prod --lan --build --force-recreate=api,web,minio
```

### Public HTTPS (Caddy)

```powershell
pnpm compose up --stack=prod --public --build
```

### Scale workers

```powershell
pnpm compose up --stack=prod --scale --build --scale-worker=2
pnpm compose scale --stack=prod --scale --worker=3
```

---

## Compose files

Under [`deploy/compose/`](./deploy/compose/). Env reference: [`deploy/ENV.md`](./deploy/ENV.md). Architecture: [docs/PLATFORM.md](./docs/PLATFORM.md).

---

## Go-live checklist

- [ ] Change default postgres/minio/grafana passwords
- [ ] `AUDIT_SEED_ON_STARTUP=false`
- [ ] `AUDIT_MINIO_PUBLIC_ENDPOINT` for uploads
- [ ] `AUDIT_CORS_ORIGINS` for your domain
- [ ] TLS in front of public ports
- [ ] `pnpm deploy:check`
