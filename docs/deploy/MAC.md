# Deploy on Mac (Apple Silicon) — end to end

**Audience:** run Repody on an M1/M2/M3 Mac laptop from Docker Hub images.  
**Time:** ~15–30 minutes first run (image pull + model warmup).  
**Secrets:** none to invent — `pnpm platform setup` copies local-dev env files for you.

Canonical map for every other deploy lane: [README.md](./README.md) · full docs hub: [../README.md](../README.md).

---

## What you get

| Layer | Where it runs |
|-------|----------------|
| API, UI, workers | Docker Hub images (`linux/arm64` on Apple Silicon) |
| Postgres, Redis, MinIO, Keycloak | Docker Compose |
| PP-OCRv6 (`:8868`) | Host — opt-in with `--with-paddle` |
| Qwen (`:8084`) | Host — with `--with-paddle` or `--with-glm` |
| NuExtract (`:8081`) | Host — **default** |
| GLM-OCR | Off unless `--with-glm` |

Default extraction pipeline: **`repody:vlm`** (NuExtract on host).

Images (public, multi-arch):

- `mehdigououiad/repody-backend:0.1.0`
- `mehdigououiad/repody-web:0.1.0`

Docker selects `linux/arm64` automatically on Apple Silicon.

---

## Prerequisites (once)

1. **Docker Desktop** for Mac — running (whale icon in menu bar).
2. **Node 24** + **pnpm 11.7.0**:
   ```bash
   # after installing Node 24
   corepack enable
   corepack prepare pnpm@11.7.0 --activate
   ```
3. **llama.cpp** (Metal-backed `llama-server` for NuExtract):
   ```bash
   brew install llama.cpp
   which llama-server   # must be on PATH
   ```
4. **NuExtract GGUFs** (required for default `pnpm platform`):
   - Download from [numind/NuExtract3-GGUF](https://huggingface.co/numind/NuExtract3-GGUF)
   - Set `LLAMACPP_MODEL` + `LLAMACPP_MMPROJ` in `deploy/llamacpp/paths.local.env`
   - See [deploy/llamacpp/README.md](../../deploy/llamacpp/README.md)
5. Disk / RAM: leave room for Hub images (~2–4 GB) and NuExtract GGUFs.

No Docker Hub login is required to **pull** (public images).

---

## Install and start

```bash
git clone https://github.com/MehdiGououiad/repody.git
cd repody
pnpm install
pnpm doctor
pnpm platform setup             # once: create env files + docker pull
# edit deploy/llamacpp/paths.local.env with NuExtract GGUF paths
pnpm platform doctor            # checks llama-server + NuExtract3 + Docker + env
pnpm platform                   # same preflight, then start
pnpm platform status
```

One-shot after clone/install:

```bash
pnpm platform bootstrap
```

### What `setup` creates (no hand-written secrets)

| File | Source | Purpose |
|------|--------|---------|
| `backend/.env` | `deploy/env/compose.env.example` | API / Compose / inference URLs |
| `.env.local` | `deploy/env.auth.example` | Next.js / Auth.js / Keycloak browser issuer |
| `deploy/llamacpp/paths.local.env` | Mac/Win example | **Required** NuExtract GGUF paths for default start |
| `deploy/research/qwen35/paths.local.env` | Mac example if present | Qwen model paths (only if `--with-paddle`) |

These are **trusted laptop / localhost** defaults. Do not expose Compose ports to a LAN or reuse passwords outside development.

### Preflight (before start)

```bash
pnpm platform doctor
```

Same checks run automatically at the start of `pnpm platform`. Required for the default path:

- Node 24 / pnpm 11  
- Docker Desktop running  
- `llama-server` on PATH (`brew install llama.cpp`)  
- NuExtract3 `.gguf` + mmproj paths on disk  
- `backend/.env` + `.env.local`  

`uv` is required only with `--with-paddle`.

---

## Sign in and verify

| What | URL / value |
|------|-------------|
| UI | http://localhost:3000 |
| API health | http://localhost:8000/v1/healthz/live |
| Keycloak | http://localhost:8080 |
| User | `operator@repody.local` |
| Password | `repody-dev` |

**Use `localhost`, not `127.0.0.1`**, in the browser (OIDC cookie / issuer host must match).

Observability (on by default):

| UI | URL |
|----|-----|
| Grafana | http://localhost:3030 |
| Bugsink | http://localhost:8090 · `admin@repody.local` / `repody-dev` |

Optional: create a Bugsink project, set `BUGSINK_DSN` in `backend/.env`, recreate `api`.

Daily commands:

```bash
pnpm platform doctor    # check llama-server + NuExtract3 + Docker + env
pnpm platform           # same preflight, then start
pnpm platform status    # health
pnpm platform logs      # container logs
pnpm platform stop      # tear down
pnpm platform help      # flags
```

---

## Env and secrets — do you need any?

| Need | Answer |
|------|--------|
| First Mac boot | **No** — setup copies examples |
| Docker Hub pull | **No login** (public) |
| Sign-in | Seeded Keycloak user above |
| Real production / OpenShift | **Yes** — Vault/ESO, real IdP — [SECRETS.md](./SECRETS.md) · [OPENSHIFT.md](./OPENSHIFT.md) |

Only edit env if you opt into extras (Bugsink DSN, NuExtract GGUF paths, custom ports).

---

## Useful flags

```bash
pnpm platform -- --platform-only          # containers only (no host models)
pnpm platform -- --with-paddle            # also PP-OCR + Qwen
pnpm platform -- --with-glm               # also GLM-OCR path
pnpm platform -- --no-nuextract           # skip NuExtract
pnpm platform -- --no-obs                 # skip Grafana/Bugsink stack
pnpm platform -- --no-pull                # skip docker pull
```

Shared flag table and catalog ids: [LOCAL.md](./LOCAL.md) · command cheat sheet: [../COMMANDS.md](../COMMANDS.md).

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `pnpm doctor` fails on Docker | Start Docker Desktop; wait until it is ready |
| `llama-server` missing | `brew install llama.cpp` and open a new terminal |
| Pull slow / timeout | Retry `pnpm platform setup`; check network |
| Wrong arch image | Re-pull: `docker pull mehdigououiad/repody-web:0.1.0` — must list `linux/arm64` in `docker buildx imagetools inspect …` |
| Login / redirect loops | Open **http://localhost:3000** (not 127.0.0.1) |
| OCR / NuExtract not ready | Set GGUF paths; `pnpm llamacpp:serve`; `pnpm platform status` |
| Port in use | Stop other stacks: `pnpm platform stop` |

Confirm Hub multi-arch (optional):

```bash
docker buildx imagetools inspect mehdigououiad/repody-backend:0.1.0
docker buildx imagetools inspect mehdigououiad/repody-web:0.1.0
# expect Platform: linux/amd64 and linux/arm64
```

---

## Related docs

| Topic | Doc |
|-------|-----|
| Same flow on Windows/Linux | [LOCAL.md](./LOCAL.md) |
| Publish / refresh Hub images | [../../deploy/registry/README.md](../../deploy/registry/README.md) |
| All commands | [../COMMANDS.md](../COMMANDS.md) |
| Cluster / OpenShift production | [OPENSHIFT.md](./OPENSHIFT.md) |
| Full documentation map | [../README.md](../README.md) |
