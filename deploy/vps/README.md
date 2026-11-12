# Repody on a VPS (Docker Compose, Tailscale, Cloudflare Tunnel)

One VPS runs the Repody stack ([`compose.yaml`](compose.yaml)) with Docker Compose. NuExtract3 runs
on Modal ([deploy/modal/README.md](../modal/README.md)). **No inbound port is open:**

```
visitors ──HTTPS──▶ Cloudflare ──tunnel──▶ cloudflared ──▶ web :3000
                    (TLS, DDoS, Access)    (outbound only)  └─▶ keycloak :8080
GitHub Actions ──Tailscale SSH──▶ deploy@vps    (ephemeral tag:ci node, no stored key)
you ───────────Tailscale SSH──▶ deploy@vps
workers ──HTTPS──▶ Modal (NuExtract3 on vLLM)
```

| Hostname | Tunnel route | Public |
|---|---|---|
| `app.example.com` | `http://web:3000`: the UI, and the API at `/api/v1` for workflow API keys | Yes |
| `auth.example.com` | `http://keycloak:8080`, paths `realms/repody` and `resources` only | Yes |
| `kc-admin.example.com` | `http://keycloak:8080`, the admin console | No, Cloudflare Access only |

The API, workers, Postgres, Redis and SeaweedFS have no route at all.

**Deploys** come from [`.github/workflows/deploy.yml`](../../.github/workflows/deploy.yml), run by
hand with a version. It does the following:
1. Checks that the three images carry this repository's release signature.
2. Joins your tailnet as an ephemeral `tag:ci` node, signing in with GitHub's OIDC token; no
   Tailscale secret is stored.
3. Sends `compose.yaml` over Tailscale SSH, and writes the version to `release.env`.
4. Pulls with that run's short-lived token, then logs the server out of the registry.
5. Runs `docker compose up -d --wait`, then checks that the public app answers.

Secrets never leave the server.

## What you need

- A VPS: Ubuntu 24.04 LTS, 4 vCPU, 8 GB RAM, 80 GB disk. The stack uses about 1.5 GB (measured,
  below).
- A domain on Cloudflare (free plan), and free Cloudflare Zero Trust and Tailscale accounts.
- A release. Push the tag `v<version>` (for example `v1.0.0`), and the images-ghcr workflow
  publishes `repody-backend`, `repody-web` and `repody-keycloak` as `<version>`, signed. It runs
  only on a commit whose CI passed.
- NuExtract3 on Modal, with its URL and a Proxy Token ([deploy/modal/README.md](../modal/README.md)).

## 1. Prepare the server (once)

Run these as root, or with `sudo`.

**Updates and Docker.** Install Docker Engine from Docker's own apt repository, following
[docs.docker.com/engine/install/ubuntu](https://docs.docker.com/engine/install/ubuntu/), with the
Compose plugin. Then turn on automatic security updates (Ubuntu's
[unattended-upgrades](https://documentation.ubuntu.com/server/how-to/software/automatic-updates/)):

```bash
apt update && apt install -y unattended-upgrades
dpkg-reconfigure -plow unattended-upgrades
```

**Docker daemon.** Create `/etc/docker/daemon.json`, then `systemctl restart docker`. It keeps
containers running through daemon restarts and rotates logs, so a noisy container can't fill the
disk:

```json
{ "live-restore": true, "userland-proxy": false,
  "log-driver": "json-file", "log-opts": { "max-size": "10m", "max-file": "3" } }
```

**Deploy user and directory.** Membership of the `docker` group is root-equivalent, so this
account is only for the stack:

```bash
adduser --disabled-password --gecos "" deploy && usermod -aG docker deploy
install -d -o deploy -g deploy -m 750 /opt/repody
```

**Tailscale and SSH.** Install Tailscale ([tailscale.com/download/linux](https://tailscale.com/download/linux)).
Then join with a tag and turn on [Tailscale SSH](https://tailscale.com/kb/1193/tailscale-ssh):

```bash
tailscale up --ssh --advertise-tags=tag:repody-server
```

In the Tailscale admin console's **Access controls**, use this policy, then tag the server
`tag:repody-server` (Machines → ⋯ → **Edit tags**) and turn off its key expiry (⋯ → **Disable key
expiry**):

```json
{
  "tagOwners": {
    "tag:repody-server": ["autogroup:admin"],
    "tag:ci": ["autogroup:admin"]
  },
  "grants": [
    { "src": ["autogroup:member"], "dst": ["*"], "ip": ["*"] },
    { "src": ["tag:ci"], "dst": ["tag:repody-server"], "ip": ["22"] }
  ],
  "ssh": [
    { "action": "accept", "src": ["autogroup:member"], "dst": ["autogroup:self"], "users": ["autogroup:nonroot", "root"] },
    { "action": "accept", "src": ["autogroup:admin"], "dst": ["tag:repody-server"], "users": ["deploy", "root"] },
    { "action": "accept", "src": ["tag:ci"], "dst": ["tag:repody-server"], "users": ["deploy"] }
  ],
  "sshTests": [
    { "src": "tag:ci", "dst": ["tag:repody-server"], "accept": ["deploy"], "deny": ["root"] }
  ]
}
```

CI's ephemeral nodes reach only the server's SSH, and only as `deploy`. The `sshTests` make Tailscale
refuse any policy that would let CI become root. A rule from a tagged device must be `accept`:
Tailscale's `check` (a fresh sign-in) is for people.

Once `tailscale ssh deploy@<server>` works from your machine, you no
longer need OpenSSH from the internet.

**Firewall.** Only the tailnet may reach the server:

```bash
ufw default deny incoming && ufw default allow outgoing
ufw allow in on tailscale0
ufw enable
```

Also add a cloud firewall at your provider that drops all inbound traffic. Docker writes its own
iptables rules and bypasses UFW for published ports. The stack publishes none, but the provider
firewall makes sure. Keep the provider's web console as your way back in.

## 2. Cloudflare Tunnel and Access

Cloudflare's guide: [create a tunnel (dashboard)](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/get-started/create-remote-tunnel/).

1. In **Zero Trust → Networks → Connectors**, create a **Cloudflared** tunnel and copy its token.
   It goes in `CLOUDFLARE_TUNNEL_TOKEN`, below. The `cloudflared` container in the stack is the
   connector.
2. In the tunnel's **Published application routes**, add the routes from the table at the top:
   - `app` with service `http://web:3000`
   - `auth`, path `realms/repody`, with service `http://keycloak:8080`
   - `auth`, path `resources`, with the same service
   - `kc-admin` with service `http://keycloak:8080`

   Keycloak's [reverse proxy guide](https://www.keycloak.org/server/reverseproxy) exposes only
   the realm and resource paths publicly.
3. In **Access → Applications**, add a self-hosted application for `kc-admin.example.com` that
   allows only your email. The admin console then needs a Cloudflare sign-in before Keycloak's
   own.

## 3. Secrets on the server

As `deploy`, in `/opt/repody`, create `.env` from [`env.example`](env.example). Generate secrets
with `openssl rand -hex 32` (hex only), then `chmod 600 .env`. A missing required value stops
the deploy with its name.

## 4. GitHub

1. Create a [Tailscale federated identity](https://tailscale.com/kb/1581/workload-identity-federation)
   (Settings → Trust credentials → Credential → OpenID Connect): issuer **GitHub**, subject
   `repo:<owner>/<repo>:environment:production`, scope **Auth Keys → Write** with the tag `tag:ci`.
   Only this repository's production deploys can then join the tailnet.
2. In the repository, create the environment **`production`** (Settings → Environments):
   - secrets `TS_OAUTH_CLIENT_ID` and `TS_AUDIENCE`, from the federated identity;
   - variables `DEPLOY_HOST` (the server's Tailscale name, for example `repody-vps`) and `APP_HOST`
     (`app.example.com`).

## 5. Deploy

Under **Actions → Deploy → Run workflow**, enter the version, for example `1.0.0`. The first
deploy creates the databases. Postgres, Redis and SeaweedFS turn healthy, `migrate` applies the
migrations and exits, then Keycloak, the API, the workers, the scheduler, web and cloudflared
start. The run fails if any health check fails, or if `https://app.example.com` doesn't answer.

**Rolling back** is the same thing: run Deploy with the previous version. The migrations are
forward-only, so check the release notes before going back across a schema change.

## 6. First sign-in

1. Go to `https://kc-admin.example.com/admin/`. Pass Cloudflare Access, then sign in to Keycloak
   with `KEYCLOAK_BOOTSTRAP_ADMIN` / `KEYCLOAK_BOOTSTRAP_PASSWORD`. Create a permanent admin in the
   **master** realm and delete the bootstrap one: it's temporary
   ([containers guide](https://www.keycloak.org/server/containers)).
2. Go to `https://app.example.com` and sign in as `REPODY_ADMIN_EMAIL`. Keycloak makes you set a
   new password and an authenticator app. Add people in the `repody` realm, with the roles
   `admin`, `operator` or `viewer`.

The realm's URLs, client secret and first admin come from `.env` when Keycloak imports it, the
first time it starts. Later deploys don't import it again: Keycloak skips a realm that already
exists ([import and export](https://www.keycloak.org/server/importExport)). After that, change them
in the admin console.

## Backups

Not set up yet. Postgres (`postgres-data`) and the uploaded documents (`seaweedfs-data`) are the
data to protect. When you add backups, test a restore before relying on them.

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
| cloudflared | (not measured) | 128 MB | |
| **Total** | **≈ 1.5 GB** | 6.5 GB | |

The limits are ceilings, not reservations, so an 8 GB VPS keeps most of its memory free. Model calls
go to Modal, 4 at a time (`AUDIT_INFERENCE_CONCURRENCY`, the vLLM server's `MAX_INPUTS`). Every
container runs with `no-new-privileges`, and the backend and web containers have read-only
filesystems with `/tmp` in memory.

## Operating it

From your machine, run `tailscale ssh deploy@<server>`, then `cd /opt/repody`:

| Task | Command |
|---|---|
| Status | `docker compose --env-file .env --env-file release.env ps` |
| Logs | `docker compose --env-file .env --env-file release.env logs -f --tail 200 api worker` |
| Restart one service | `docker compose --env-file .env --env-file release.env restart worker` |
| Disk | `docker system df` |

## Troubleshooting

| Symptom | Check |
|---|---|
| Deploy stops with `required variable … is missing` | That variable in `/opt/repody/.env` |
| `Join the tailnet` fails | The federated identity's tag is `tag:ci`, and the policy has the `tag:ci` owner, grant and SSH rule |
| 502 from the app host | `docker compose … logs cloudflared`; the tunnel routes use the service names `web` and `keycloak` |
| Sign-in fails with `invalid redirect_uri` | `APP_HOST` matches the domain; it was baked into the realm on first import (fix it in the admin console) |
| A run fails with a model timeout right after a Modal deploy | Wake the model first (deploy/modal/README.md, "Check it") |
| `migrate` exited with an error | `docker compose … logs migrate`; the API and workers wait for it |
