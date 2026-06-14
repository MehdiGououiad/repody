# Deploy Repody to the cloud

Run Repody on a **Linux VPS** in the cloud. Your PC is only used to push code or SSH in once — users access Repody over HTTPS.

**Architecture**

| Layer | Where | Cost model |
|-------|--------|------------|
| Web, API, workers, Postgres, Redis, MinIO, Hatchet | Your VPS (Docker Compose) | ~$12–24/mo |
| Repody VLM inference | Customer GPU / vLLM (on-prem or separate host) | Your infra |

No GPU is required on the VPS.

## 1. Pick a server

Recommended (4 vCPU, 8 GB RAM minimum):

| Provider | Example plan | Region |
|----------|--------------|--------|
| [Hetzner](https://www.hetzner.com/cloud) | CPX31 | EU/US |
| [DigitalOcean](https://www.digitalocean.com) | 4 GB Droplet | nearest to users |
| [Vultr](https://www.vultr.com) | 4 vCPU / 8 GB | nearest to users |

OS: **Ubuntu 22.04 or 24.04**.

Open firewall: **TCP 80, 443** only (provider firewall + `ufw`).

## 2. DNS

Point two hostnames to the VPS public IP:

| Record | Example |
|--------|---------|
| `A` | `app.yourdomain.com` → VPS IP |
| `A` | `files.yourdomain.com` → VPS IP |

Both can be the same IP; Caddy routes by hostname.

## 3. GPU / vLLM (Repody VLM)

Repody does not ship GPU inference on the VPS. Point it at an OpenAI-compatible vLLM service running **Repody VLM**.

See **[docs/REPODY-VLM.md](./docs/REPODY-VLM.md)** for:

- `vllm serve` flags (vision limits, chat template, MTP)
- Platform env vars (`AUDIT_VLLM_BASE_URL`, optional `AUDIT_VLLM_API_KEY`)
- Bundled GPU stack via `pnpm docker:deploy:gpu` if the customer runs GPU on the same machine

Copy-paste env block: [`deploy/repody-vlm.env.example`](./deploy/repody-vlm.env.example).

## 4. Install on the server

SSH into the VPS:

```bash
ssh root@YOUR_VPS_IP
```

### Option A — clone from Git

```bash
apt-get update && apt-get install -y git
git clone https://github.com/YOUR_ORG/agentcontrol.git
cd agentcontrol
```

### Option B — copy from your PC

```powershell
# From your dev machine (replace user/host/path)
scp -r C:\Users\Mehdi\OneDrive\Desktop\agentcontrol root@YOUR_VPS_IP:/opt/repody
ssh root@YOUR_VPS_IP
cd /opt/repody
```

## 5. Configure secrets

On the server:

```bash
chmod +x deploy/cloud/*.sh
bash deploy/cloud/setup-env.sh
```

You will enter:

- `PUBLIC_DOMAIN` (e.g. `app.yourdomain.com`)
- `FILES_DOMAIN` (e.g. `files.yourdomain.com`)
- Basic-auth username/password (**share this with users** — the UI has no separate login)
- vLLM base URL (and API key if required)

This writes `.env` with generated admin token, DB password, and MinIO password.

## 6. Deploy

```bash
bash deploy/cloud/bootstrap.sh
```

First build takes **10–20 minutes**. Caddy obtains Let's Encrypt certificates automatically.

## 7. Share with users

Send them:

- URL: `https://app.yourdomain.com`
- Basic-auth username + password from setup

They can build workflows, upload documents, and run extractions. Repody VLM runs on the configured vLLM service when a document is processed.

### Workflow API (integrations)

In the UI: **Workflow → Deploy** → copy the workflow API key. External systems call the API with `Authorization: Bearer <key>`.

## 8. Updates

```bash
cd /opt/repody   # or your path
git pull
bash deploy/cloud/bootstrap.sh
```

## Verify

```bash
curl -s https://app.yourdomain.com/api/v1/healthz | head -c 200
```

From your PC (with DNS live):

```powershell
pnpm test:platform:integration -- --api https://app.yourdomain.com --token YOUR_ADMIN_TOKEN
```

## Environment reference

See [`.env.cloud.example`](./.env.cloud.example).

| Variable | Purpose |
|----------|---------|
| `PUBLIC_DOMAIN` | Web UI hostname |
| `FILES_DOMAIN` | MinIO uploads hostname (HTTPS via Caddy) |
| `BASIC_AUTH_*` | Protects the whole UI |
| `AUDIT_ADMIN_API_TOKEN` | Server-side API auth (auto-injected by Next.js) |
| `AUDIT_VLLM_BASE_URL` | OpenAI-compatible vLLM URL (`…/v1`) |
| `AUDIT_VLLM_API_KEY` | Optional bearer token for vLLM |

## Security notes

- Only ports **80/443** are exposed (`compose.cloud.yaml` removes all other host ports).
- Change default secrets — `setup-env.sh` generates new ones.
- Basic auth is **required** for sharing; without it, anyone with the URL has full admin access.
- Rotate `AUDIT_VLLM_API_KEY` if it was ever committed or shared in chat.

## Optional: scale workers

SSH to the server and scale OCR workers for more concurrent users:

```bash
docker compose --env-file .env \
  -f compose.yaml -f compose.cpu.yaml -f compose.prod.yaml \
  -f compose.public.yaml -f compose.cloud.yaml -f compose.scale.yaml \
  --profile web up -d --scale worker=2
```

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Upload fails in browser | Check `FILES_DOMAIN` DNS and Caddy logs: `docker compose … logs caddy` |
| Extraction timeout | GPU warm-up; increase `AUDIT_REPODY_VLM_TIMEOUT_SECONDS`; verify vLLM `/v1/models` |
| 502 on app URL | Wait for API health: `docker compose … logs api` |
| TLS certificate error | DNS must point to VPS before bootstrap; retry `docker compose … restart caddy` |

## Cost estimate (typical)

| Item | ~Monthly |
|------|----------|
| VPS 8 GB | $15–24 |
| Customer GPU / vLLM | (customer infra) |
| Domain | ~$1 |

---

Local dev remains on your PC with `pnpm docker:deploy`. Cloud deploy is independent.
