# Local platform (Windows · macOS · Linux)

One flow everywhere: **setup (env + pull) → start**.

Images: `mehdigououiad/repody-backend` + `mehdigououiad/repody-web` (`linux/amd64` + `linux/arm64`).

## New PC

```bash
# Docker Desktop running
# Node 24 + pnpm 11: corepack enable
# llama-server on PATH (Qwen / optional NuExtract)
#   macOS:  brew install llama.cpp
#   Windows: winget install ggml.llamacpp

git clone https://github.com/MehdiGououiad/repody.git
cd repody
pnpm install
pnpm doctor
pnpm platform setup             # env files + docker pull Hub images
pnpm platform                   # start API/UI/workers + PP-OCR + Qwen
# or one shot after install: pnpm platform bootstrap
pnpm platform status
```

PP-OCR Python deps **auto-install** on first OCR start.

| Layer | Source |
|-------|--------|
| API / UI / workers | Docker Hub |
| Postgres / Redis / MinIO / Keycloak | Compose |
| PP-OCRv6 `:8868` | Host (auto-install) |
| Qwen `:8084` | Host |
| NuExtract / GLM | Off unless flagged |

**Default extraction:** `paddleocr:qwen`

Sign-in: http://localhost:3000 · `operator@repody.local` / `repody-dev`  
Use **localhost**, not `127.0.0.1`.

Hub auth wiring: browser issuer is `http://localhost:8080/realms/repody`; the web
container uses `AUTH_KEYCLOAK_INTERNAL_ISSUER=http://keycloak:8080/realms/repody`
for server-side token calls. API fetches JWKS from `http://keycloak:8080/...`.

Observability is **on by default** (`--no-obs` to skip):

| UI | URL |
|----|-----|
| Grafana (Loki logs / Tempo traces) | http://localhost:3030 |
| Bugsink (exceptions) | http://localhost:8090 · `admin@repody.local` / `repody-dev` |

Tail containers: `pnpm platform logs`.  
Bugsink needs a project DSN in `backend/.env` (`BUGSINK_DSN=…`) then recreate `api`.

## Daily

```bash
pnpm platform
pnpm platform status
pnpm platform stop
pnpm platform help
```

## Options

```bash
pnpm platform -- --with-nuextract
pnpm platform -- --platform-only
pnpm platform -- --no-paddle
pnpm platform -- --no-qwen
pnpm platform -- --with-glm
pnpm platform -- --no-pull
pnpm platform setup -- --no-pull
```

| Flag | Effect |
|------|--------|
| `--with-nuextract` | NuExtract `:8081` (set GGUF paths in `deploy/llamacpp/paths.local.env`) |
| `--with-glm` | GLM-OCR (experimental on Hub image) |
| `--no-paddle` / `--no-qwen` | Skip host models |
| `--platform-only` | Containers only |
| `--no-pull` | Skip `docker pull` (setup + up) |

## CLI map

| Command | Purpose |
|---------|---------|
| `pnpm platform setup` | Once — env + pull Hub images |
| `pnpm platform` | Start |
| `pnpm platform doctor` | Prereqs |
| `pnpm platform status` | Health |
| `pnpm platform stop` | Tear down |
| `pnpm platform help` | Flags |

Aliases: `pnpm dev:all` → start · `pnpm dev:setup` / `dev:status` / `dev:stop` → same CLI.

## Develop from source (contributors)

```bash
pnpm dev:src:all    # local-dev: host API/UI + local worker build
pnpm dev:app        # foreground API + UI only
```

## Related

- Overlay: [`compose.portable.yaml`](../../compose.portable.yaml)
- Registry: [`deploy/registry/README.md`](../../deploy/registry/README.md)
- Helm Hub values: [`deploy/client/values-dockerhub.example.yaml`](../../deploy/client/values-dockerhub.example.yaml)
