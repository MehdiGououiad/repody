# Repody on a VPS with Dokploy

One VPS runs [Dokploy](https://docs.dokploy.com) (v0.31.1) and the Repody stack
([`compose.yaml`](compose.yaml)). The model, NuExtract3, runs on Modal
([deploy/modal/README.md](../modal/README.md)). Visitors reach the VPS only through a
**Cloudflare Tunnel**, and you reach it only through **Tailscale**: no inbound port is open.

```
browser ──HTTPS──▶ Cloudflare ──tunnel──▶ cloudflared ──▶ Dokploy's Traefik ──▶ web :3000
                   (TLS, DDoS)            (outbound only)                   └─▶ keycloak :8080
you ──Tailscale──▶ SSH, Dokploy UI (:3000)
workers ──HTTPS──▶ Modal (NuExtract3 on vLLM)
```

| Hostname | Goes to | Public |
|---|---|---|
| `app.example.com` | web (the UI, and the API at `/api/v1` for workflow API keys) | Yes |
| `auth.example.com` | Keycloak sign-in: `/realms/repody` and `/resources` only | Yes |
| `kc-admin.example.com` | Keycloak admin console | No, behind Cloudflare Access |

The API, workers, Postgres, Redis and SeaweedFS have no hostname. They are reachable only on the
stack's own network.

## What you need

- A VPS: Ubuntu 24.04 LTS, 4 vCPU, 8 GB RAM, 80 GB disk. Dokploy needs at least 2 GB and
  30 GB ([installation](https://docs.dokploy.com/docs/core/installation)); Repody's limits add
  up to about 6.5 GB, below.
- A domain whose DNS is on Cloudflare (free plan), and a free Tailscale account.
- Released images. Push the tag `v<version>` (for example `v1.0.0`), and
  `.github/workflows/images-ghcr.yml` publishes `repody-backend`, `repody-web` and
  `repody-keycloak` as `<version>`, signed. It runs only on a commit whose CI passed.
- NuExtract3 deployed on Modal, with its URL and a Proxy Token ([deploy/modal/README.md](../modal/README.md)).

## 1. Harden the server

These are the host steps from Dokploy's
[Production Hardening Guide](https://docs.dokploy.com/docs/core/guides/production-hardening).
Run them as root, or with `sudo`, before installing Dokploy.

```bash
apt update && apt install -y unattended-upgrades apt-listchanges fail2ban ufw
dpkg-reconfigure -plow unattended-upgrades
```

**SSH.** Put your key in `~/.ssh/authorized_keys` first. Then set these in `/etc/ssh/sshd_config`,
and `systemctl reload ssh`, keeping your current session open until a new login works:

```
PubkeyAuthentication yes
PasswordAuthentication no
PermitRootLogin no
```

**Fail2Ban.** Use the guide's `jail.local` with `[sshd] enabled = true`, then
`systemctl enable --now fail2ban`.

**Docker daemon.** The guide's `/etc/docker/daemon.json`. Docker comes with Dokploy, so apply
this right after step 2:

```json
{ "live-restore": true, "userland-proxy": false,
  "log-driver": "json-file", "log-opts": { "max-size": "10m", "max-file": "3" } }
```

**Tailscale.** Install it per [tailscale.com/download/linux](https://tailscale.com/download/linux),
then `tailscale up`. From now on, connect over the server's Tailscale name or IP.

**Firewall.** With the tunnel, nothing needs to come in from the internet. Only Tailscale may reach
SSH and the Dokploy UI:

```bash
ufw default deny incoming && ufw default allow outgoing
ufw allow in on tailscale0
ufw enable
```

Also add a cloud firewall at your provider that drops all inbound traffic. Docker writes its own
iptables rules and bypasses UFW for published ports. The stack publishes none, but the provider
firewall makes sure.

## 2. Install Dokploy (pinned)

Every Dokploy release ships its own installer
([installation](https://docs.dokploy.com/docs/core/installation#install-specific-versions)):

```bash
curl -sL https://github.com/Dokploy/dokploy/releases/download/v0.31.1/install.sh | sh
```

Open `http://<tailscale-ip>:3000`, create the admin account, and turn on **2FA or a passkey**
([account security](https://docs.dokploy.com/docs/core/account-security)). Port 3000 stays
closed to the internet: the firewall above only lets Tailscale in.

Updates use the release's installer the same way, with `sh -s update`.

## 3. Cloudflare Tunnel

From [Dokploy's Cloudflare Tunnels guide](https://docs.dokploy.com/docs/core/guides/cloudflare-tunnels):

1. In Cloudflare, go to **Zero Trust → Networks → Connectors**, create a tunnel (type
   Cloudflared), and copy its token.
2. Under **SSL/TLS**, set the mode to **Full** (not Flexible).
3. In Dokploy, create an **Application** with the Docker provider and the image
   `cloudflare/cloudflared:2026.11.0`. Set the environment to `TUNNEL_TOKEN=<token>`, the
   arguments to `tunnel` and `run`, then deploy.
4. In the tunnel's **Published application routes**, add `app`, `auth` and `kc-admin` on your
   domain. Each is of type **HTTP** with the URL `dokploy-traefik:80`.
5. In **Zero Trust → Access → Applications**, add a self-hosted application for
   `kc-admin.example.com` that allows only your email. The Keycloak admin console then needs a
   Cloudflare sign-in before Keycloak's own.

Cloudflare terminates TLS, so Dokploy's domains below use **HTTP with no certificate**, as the
guide says.

## 4. The GHCR registry

In Dokploy, open **Registry** and add `ghcr.io`, with your GitHub user and a token that has only
`read:packages` and an expiry date
([registry](https://docs.dokploy.com/docs/core/registry)).

## 5. The Repody stack

1. Create a project, then a **Compose** service of type **Docker Compose**. For the source, use
   Git (this repository, branch `master`, path `deploy/dokploy/compose.yaml`), or **Raw** with
   that file pasted in.
2. Under **Advanced**, turn on **Isolated Deployments**, so the stack gets its own network and
   Traefik joins it ([utilities](https://docs.dokploy.com/docs/core/docker-compose/utilities)).
3. In **Environment**, paste [`env.example`](env.example) and fill in every value. Generate secrets
   with `openssl rand -hex 32`, hex only. A missing required value stops the deploy with its name.
4. In **Domains**, add these entries, all HTTP with no HTTPS toggle and no certificate:

   | Service | Port | Host | Path |
   |---|---|---|---|
   | `web` | 3000 | `app.example.com` | `/` |
   | `keycloak` | 8080 | `auth.example.com` | `/realms/repody` |
   | `keycloak` | 8080 | `auth.example.com` | `/resources` |
   | `keycloak` | 8080 | `kc-admin.example.com` | `/` |

   Keycloak's [reverse proxy guide](https://www.keycloak.org/server/reverseproxy) exposes only
   the realm and resource paths publicly. The admin console gets its own host
   (`KC_HOSTNAME_ADMIN`), behind Cloudflare Access.
5. Deploy. The order is: Postgres, Redis and SeaweedFS turn healthy, `migrate` applies the
   migrations and exits, then Keycloak, the API, workers, the scheduler and web start.

## 6. First sign-in

1. Go to `https://kc-admin.example.com/admin/`. Pass Cloudflare Access, then sign in to Keycloak
   with `KEYCLOAK_BOOTSTRAP_ADMIN` / `KEYCLOAK_BOOTSTRAP_PASSWORD`. Create a permanent admin in the
   **master** realm and delete the bootstrap one: Keycloak's bootstrap admin is temporary
   ([containers guide](https://www.keycloak.org/server/containers)). You can then remove those
   two variables.
2. Go to `https://app.example.com` and sign in as `REPODY_ADMIN_EMAIL`, with
   `REPODY_ADMIN_INITIAL_PASSWORD`. Keycloak makes you set a new password and an authenticator
   app. Add more people in the `repody` realm, with the roles `admin`, `operator` or `viewer`.

The realm's URLs, client secret and first admin come from the environment when Keycloak imports
it, the first time it starts. Later deploys don't import it again: Keycloak skips a realm that
already exists ([import and export](https://www.keycloak.org/server/importExport)). After that,
change them in the admin console.

## 7. Backups

Dokploy's [Volume Backups](https://docs.dokploy.com/docs/core/volume-backups) copy named volumes
to S3. A Cloudflare R2 bucket works and is free up to 10 GB.

1. Under **Settings → S3 Destinations**, add the bucket. Use a key scoped to that bucket only, and
   turn on encryption at rest on the bucket: Dokploy doesn't encrypt the archives.
2. In the stack's **Volume Backups**, add `postgres-data`, `seaweedfs-data` and `redis-data`.
   Use a nightly cron (for example `0 3 * * *`) and **Container OFF**, so each volume is copied
   while its service is stopped, a few seconds per volume.
3. **Test a restore** (Volume Backups → Restore Volume) before you rely on the backups, and
   again every quarter.

## Resources

Measured on 12 November 2026, after a full extraction run (`docker stats`):

| Service | Used | Limit | Notes |
|---|---|---|---|
| keycloak | 645 MB | 1.5 GB | Optimized build; the JVM takes 70% of the limit, and Keycloak advises at least 750 MB; healthy in about 14 s |
| worker | 247 MB | 1.5 GB | Renders PDF pages; up to `AUDIT_WORKER_CONCURRENCY` runs at once |
| api | 166 MB | 768 MB | |
| scheduler | 137 MB | 256 MB | |
| postgres | 105 MB | 1 GB | `shared_buffers=256MB`, 256 MB `shm_size` |
| web | 77 MB | 512 MB | Next.js standalone server |
| seaweedfs | 73 MB | 512 MB | |
| redis | 9 MB | 384 MB | `maxmemory 256mb`, `noeviction`, append-only (the run queue) |
| **Total** | **≈ 1.5 GB** | 6.4 GB | |

The limits are ceilings, not reservations. Even with Dokploy's own ~1.5 GB, an 8 GB VPS keeps most
of its memory free. Model calls go to Modal, 4 at a time (`AUDIT_INFERENCE_CONCURRENCY`, the
vLLM server's `MAX_INPUTS`). Every container runs with `no-new-privileges`, and the backend and
web containers have read-only filesystems with `/tmp` in memory.

## Updating

- **Repody:** push a new tag `v<version>`, wait for the signed images, change `REPODY_VERSION`
  in the Environment tab, then **Redeploy**. Migrations run first, automatically.
- **Dokploy:** run the new release's `install.sh` with `sh -s update`.
- **The model:** see [deploy/modal/README.md](../modal/README.md). After a `modal deploy`, wake it
  once; its first start takes a few minutes.

## Troubleshooting

| Symptom | Check |
|---|---|
| Deploy stops with `required variable … is missing` | The named variable in the Environment tab |
| 502 or 404 from the app host | The tunnel route points to `dokploy-traefik:80`, the domain is HTTP without a certificate, and Isolated Deployments is on |
| Redirect loop | Cloudflare SSL/TLS mode is Flexible: set it to **Full** |
| Sign-in fails with `invalid redirect_uri` | `APP_HOST` matches the domain; it was baked into the realm on first import (fix it in the admin console) |
| A run fails with a model timeout right after a Modal deploy | Wake the model first (deploy/modal/README.md, "Check it") |
| `migrate` failed | Its logs in Dokploy; the API and workers wait for it |
