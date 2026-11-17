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

The API, workers, Postgres, Hatchet and SeaweedFS have no route at all. Hatchet's dashboard
listens on the server's loopback only ([Hatchet](#hatchet)).

**Deploys** come from [`.github/workflows/deploy.yml`](../../.github/workflows/deploy.yml):

- **Staging:** CI builds each `master` commit whose tests pass and deploys it to
  [staging](#staging).
- **Production:** a release tag promotes that same build ([Releasing](#releasing)).
- **By hand:** you can run it yourself with a version and a target.

It does the following:
1. Checks that the three images carry this repository's build signature from `master`, and pins
   the server to the digests it verified.
2. Joins your tailnet as an ephemeral `tag:ci` node, signing in with GitHub's OIDC token; no
   Tailscale secret is stored.
3. Sends `compose.yaml` over Tailscale SSH, and writes the version to `release.env`.
4. Pulls with that run's short-lived token, then logs the server out of the registry.
5. Runs `docker compose up -d --wait`, then checks that the public app answers.
6. Runs the [smoke test](#tools) when the stack has a tester account.

Secrets never leave the server.

## What you need

- A VPS: Ubuntu 24.04 LTS, 4 vCPU, 8 GB RAM, 80 GB disk. The stack uses about 1.5 GB (measured,
  below).
- A domain on Cloudflare (free plan), and free Cloudflare Zero Trust and Tailscale accounts.
- Published images. Every master commit whose CI passes publishes `repody-backend`,
  `repody-web` and `repody-keycloak`, signed, tagged with the commit (`ci.yml` and
  `images-ghcr.yml`). A release tag `v<version>` (for example `v1.0.0`) on such a commit promotes
  those same images as `<version>` (`release.yml`).
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
4. In the zone's **Security → WAF → Rate limiting rules**, add one rule (the free plan's only
   one): requests matching `(http.request.method eq "POST" and http.request.uri.path wildcard
   "/api/v1/workflows/*/runs")`, 20 per 10 seconds per IP, then block for 10 seconds. Uploads are
   the one public route that carries large bodies; the API refuses an unknown caller before
   reading one, and this keeps a flood from reaching the server at all.

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
     (`app.example.com`);
   - **Deployment branches and tags:** selected ones, only the tag pattern `v*`. Nothing but a
     release tag can then deploy to production, or get its Tailscale identity.

## 5. Deploy

Push a release tag ([Releasing](#releasing)), or run **Actions → Deploy → Run workflow** from
that tag (*Use workflow from → Tags*), with its version, for example `1.0.0`. The first
deploy creates the databases. Postgres and SeaweedFS turn healthy, then Hatchet Lite; `migrate`
applies the migrations and `hatchet-token` writes a new Hatchet API token, and both exit; then
Keycloak, the API, the workers, web and cloudflared start. The run fails if any health check fails, or if `https://app.example.com` doesn't answer.

**Rolling back** is the same thing: run Deploy from the previous version's tag. The migrations are
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

## Tools

Each deploy copies these to `tools/` in the stack's directory (the release's own versions). Run
them from that directory (`/opt/repody`, or `/home/deploy/repody-staging` for staging):

| Tool | What it does |
|---|---|
| `sh tools/setup-admin-client.sh` | Adds the admin area's Keycloak account (`repody-admin`) to a realm imported before 1.5 |
| `sh tools/setup-tester-client.sh` | Creates the smoke test's account: the service account `repody-tester`, operator in the client company `client-repody-test`; its secret (`TESTER_CLIENT_SECRET`) is created in `.env` and never printed. On staging only, also `tester@staging.repody.com`, a person in the same company who signs in in the browser for UI tests (password `UI_TESTER_PASSWORD` in `.env`) |
| `tools/smoke_test.py` | One real run, end to end, as `repody-tester`: a generated one-page invoice through extraction on the GPU, the report, the credits charged, and nothing visible outside its company. A few credits and a little GPU time per run |

Each deploy runs the smoke test by itself once the stack has the tester account. To run it by hand:

```bash
export TESTER_CLIENT_SECRET=$(grep '^TESTER_CLIENT_SECRET=' .env | cut -d= -f2-)
docker compose --env-file .env --env-file release.env exec -T -e TESTER_CLIENT_SECRET api python - < tools/smoke_test.py
```

The test company (`client-repody-test`) shows in Admin like any client: its credits are topped up
automatically when low (100 at a time), and its runs count in the GPU spend.

## Releasing

Build once, deploy twice: production runs exactly the images staging tested.

1. **Merge to `master`.** CI tests the commit, builds and signs its images (tagged with the
   commit's first 12 characters), and deploys them to staging with the smoke test.
2. **Check staging**, then tag that commit:

   ```bash
   git tag v1.7.0 <commit> && git push origin v1.7.0
   ```

   `release.yml` checks that the commit is on `master` and that its images carry `master`'s
   build signature. It tags those images `1.7.0` by digest, without rebuilding, and deploys them
   to production. Tagging a commit CI has not built yet fails with a message: re-run it once
   staging has that commit.
3. **To try a branch on staging before merging**, tag it as a pre-release:
   `git tag v1.7.0-rc.1 && git push origin v1.7.0-rc.1`. CI tests and builds it, and deploys it
   to staging only. The next merge to `master` replaces it.

**Rolling back:** run **Actions → Deploy** from the older release's tag (*Use workflow from →
Tags → v1.6.2*) with that version and the target `production`.

## Staging

Staging is a second, separate copy of the stack on the same server. It runs every commit merged
to `master` a few minutes after the merge, so production only ever gets what has already run
there. It shares nothing with production except the server and the Docker engine:

| | Production | Staging |
|---|---|---|
| Directory, Compose project | `/opt/repody`, `repody` | `/home/deploy/repody-staging`, `repody-staging` (`COMPOSE_PROJECT_NAME` in its `.env`) |
| Data | its volumes and network | its own (`repody-staging_*`): its own Postgres, Keycloak, Hatchet and SeaweedFS |
| Secrets | `/opt/repody/.env` | its own `.env`, generated on the server; never copied from production |
| Hostnames | `app`, `auth`, `kc-admin` `.repody.com` | `staging`, `staging-auth`, `staging-kc-admin` `.repody.com` |
| Tunnel | `repody` | `repody-staging`: its own token |
| Who can reach it | the public (sign-in pages); the admin console behind Cloudflare Access | **everything** behind Cloudflare Access (application *Repody staging*): your email, and the deploy's service token |
| GPU | Modal environment `main` | Modal environment `staging`: its own app, weights volume and proxy token, so staging never queues behind a client's run |
| Deploys | a `v*` tag, promoting the build staging ran | each `master` commit (images tagged with the commit), or a pre-release tag such as `v1.7.0-rc.1` |
| GitHub environment | `production` | `staging` |
| Admin and testers | your account | `admin@staging.repody.com`, and the testers (`sh tools/setup-tester-client.sh`) |
| Access requests | on (the site's form) | off |
| Hatchet dashboard | `127.0.0.1:8888` | `127.0.0.1:8889` |

Each deploy checks that the stack's `.env` names the Compose project it expects before it touches
anything, so a wrong directory or variable stops the deploy instead of recreating the other
stack. Both stacks share the server's memory, disk and Docker engine; the memory limits keep
staging from starving production. Moving staging to its own server later means changing only the
`DEPLOY_HOST` variable of the `staging` environment.

### Setting it up (once)

1. **Cloudflare.** Create a second tunnel, `repody-staging`, with the same routes as production
   on the staging hostnames, and the self-hosted Access application *Repody staging* covering
   the three hostnames. Give it two policies: **Allow** your email, and **Service Auth** for a
   service token (`repody-staging-deploy`, Access → Service credentials). The token's client ID
   and secret go in the `staging` environment's secrets `CF_ACCESS_CLIENT_ID` and
   `CF_ACCESS_CLIENT_SECRET`, so the deploy's checks pass Access.
2. **Modal.** `modal environment create staging`, then
   `modal run --env staging deploy/modal/nuextract.py::download` and
   `modal deploy --env staging deploy/modal/nuextract.py`. Create a proxy token for it
   (`modal workspace proxy-tokens create --name repody-staging`).
3. **Server.** As `deploy`, create `/home/deploy/repody-staging/.env` (mode 600) from
   [`env.example`](env.example), with new secrets and these values:

   ```bash
   COMPOSE_PROJECT_NAME=repody-staging
   DEPLOYMENT_ENVIRONMENT=staging
   HATCHET_DASHBOARD_PORT=8889
   ACCESS_REQUESTS_ENABLED=false
   CORS_ORIGINS=
   APP_HOST=staging.repody.com
   AUTH_HOST=staging-auth.repody.com
   KEYCLOAK_ADMIN_HOST=staging-kc-admin.repody.com
   REPODY_ADMIN_EMAIL=admin@staging.repody.com
   MODAL_URL=https://<workspace>-staging--repody-nuextract-vllm-serve.us-east.modal.run
   ```

4. **Tailscale.** Add a second federated identity like production's (step 4 of the setup), with
   the subject `repo:<owner>/<repo>:environment:staging`, and the tag `tag:ci`. Each environment
   has its own identity, so you can revoke one without the other.
5. **GitHub.** Create the environment **`staging`** with:
   - the secrets `TS_OAUTH_CLIENT_ID` and `TS_AUDIENCE` from that identity, and
     `CF_ACCESS_CLIENT_ID` and `CF_ACCESS_CLIENT_SECRET`;
   - the variables `DEPLOY_HOST` (the same server), `APP_HOST=staging.repody.com`,
     `STACK_DIR=/home/deploy/repody-staging` and `COMPOSE_PROJECT=repody-staging`;
   - **Deployment branches and tags:** selected ones, the branch `master` and the tag pattern
     `v*-*`. In the `production` environment, only the tag pattern `v*`. A branch then cannot
     reach either stack, even by running the workflow by hand.
6. **First deploy.** Run **Actions → Deploy** with the target `staging` and the latest version.
   Then, in the staging directory, run `sh tools/setup-tester-client.sh`. From then on, each deploy
   runs the smoke test there too.

To open staging, go to `https://staging.repody.com` and pass Cloudflare Access with your email.
Then sign in as `tester@staging.repody.com` (a client operator) or `admin@staging.repody.com` (the
platform admin: its first password is `REPODY_ADMIN_INITIAL_PASSWORD`, and like production it must
change it and set up an authenticator app). Staging's data is test data only: never put a
client's documents there.

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
| hatchet-lite | (not measured) | 768 MB | Hatchet's engine, API and dashboard; its queue is the `hatchet` database |
| postgres | 105 MB | 1 GB | `shared_buffers=256MB`, 256 MB `shm_size` |
| web | 77 MB | 512 MB | Next.js standalone server |
| seaweedfs | 73 MB | 512 MB | |
| cloudflared | (not measured) | 128 MB | |
| **Total** | **≈ 1.5 GB** | 6.5 GB | |

The limits are ceilings, not reservations, so an 8 GB VPS keeps most of its memory free. Model calls
go to Modal, 4 at a time (`AUDIT_INFERENCE_CONCURRENCY`, the vLLM server's `MAX_INPUTS`). Every
container runs with `no-new-privileges`, and the backend and web containers have read-only
filesystems with `/tmp` in memory.

## Hatchet

Hatchet Lite queues the runs, enforces their timeouts and per-client limits, and runs the
maintenance cron. Its dashboard (runs, workers, the cron) listens on the server's loopback:

```bash
ssh -N -L 8888:127.0.0.1:8888 deploy@<server>
```

Then open `http://localhost:8888` and sign in as `REPODY_ADMIN_EMAIL` with `HATCHET_ADMIN_PASSWORD`.
Its config and keys live in the `hatchet-config` volume; run history is kept 7 days. The API and
workers never need a token in `.env`: `hatchet-token` writes a new one on every deploy.

## Operating it

From your machine, run `tailscale ssh deploy@<server>`, then `cd /opt/repody` (or
`cd ~/repody-staging`: its `.env` names its own project, so the same commands act on staging only):

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
