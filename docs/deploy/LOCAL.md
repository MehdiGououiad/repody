# Local platform (Windows · macOS · Linux)

One flow everywhere: **setup (env + pull) → start**.

**Apple Silicon Mac?** Prefer the dedicated walkthrough: **[MAC.md](./MAC.md)** (prereqs, env, sign-in, troubleshooting).

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
pnpm platform                   # start API/UI/workers + host NuExtract
# or one shot after install: pnpm platform bootstrap
pnpm platform status
```

PP-OCR is **opt-in** (`--with-paddle`); Python deps auto-install on first OCR start if you enable it.

| Layer | Source |
|-------|--------|
| API / UI / workers | Docker Hub |
| Postgres / Redis / MinIO / Keycloak | Compose |
| NuExtract `:8081` | Host (default) |
| PP-OCRv6 `:8868` / Qwen `:8084` | Host (`--with-paddle`) |
| GLM | Off unless `--with-glm` |

**Default extraction:** `repody:vlm` (NuExtract on host)

Sign-in: http://localhost:3000 · `operator@repody.local` / `repody-dev`  
Use **localhost**, not `127.0.0.1`.

Compose defaults (Postgres/Redis/MinIO/Keycloak/Grafana passwords, open host ports)
are for a **trusted laptop / loopback only**. Do not expose Compose to a LAN or the
internet, and never reuse these credentials outside `development`.

Hub auth wiring: browser issuer is `http://localhost:8080/realms/repody`; the web
container uses `AUTH_KEYCLOAK_INTERNAL_ISSUER=http://keycloak:8080/realms/repody`
for server-side token calls. API fetches JWKS from `http://keycloak:8080/...`.

UI → API: Next.js proxies `/api/v1/*` at **runtime** (`INTERNAL_API_URL=http://api:8000`
in Compose; Kubernetes sets `http://repody-api:8000`). The same web image works on
both — no bake-time rewrite to a fixed hostname.

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
pnpm platform -- --with-paddle
pnpm platform -- --platform-only
pnpm platform -- --no-nuextract
pnpm platform -- --with-glm
pnpm platform -- --no-pull
pnpm platform setup -- --no-pull
```

| Flag | Effect |
|------|--------|
| (default) | Host NuExtract `:8081` → `repody:vlm` (set GGUF paths in `deploy/llamacpp/paths.local.env`) |
| `--with-paddle` | Also PP-OCRv6 + Qwen → `paddleocr:qwen` |
| `--with-glm` | GLM-OCR `:8083` + rebuild extract worker with official GlmOcr SDK → `glm:qwen` / `glm:ocr` |
| `--no-nuextract` | Skip NuExtract |
| `--platform-only` | Containers only |
| `--no-pull` | Skip `docker pull` (setup + up) |

All three structured engines together:

```bash
pnpm platform -- --with-paddle --with-glm
```

| Catalog | Pipeline |
|---------|----------|
| `repody:vlm` | Official NuExtract template JSON (**default**) |
| `paddleocr:qwen` | Official PP-OCR serving → Qwen text→JSON |
| `glm:qwen` | Official GlmOcr SDK → Qwen text→JSON |

Markdown-only OCR (`paddleocr:v6`, `glm:ocr`) is not a UI option — only used inside the Qwen pipelines.

## CLI map

| Command | Purpose |
|---------|---------|
| `pnpm platform setup` | Once — env + pull Hub images |
| `pnpm platform doctor` | Preflight (llama-server, NuExtract3 GGUFs, Docker, …) |
| `pnpm platform` | Preflight + start |
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

- **Mac walkthrough:** [MAC.md](./MAC.md)
- Overlay: [`compose.portable.yaml`](../../compose.portable.yaml)
- Registry: [`deploy/registry/README.md`](../../deploy/registry/README.md)
- Helm Hub values: [`deploy/client/values-dockerhub.example.yaml`](../../deploy/client/values-dockerhub.example.yaml)
- Docs hub: [`../README.md`](../README.md)

## Cluster install (not local daily path)

Local daily work stays on Compose (`pnpm platform`). For Kubernetes / OpenShift production:

→ [OPENSHIFT.md](./OPENSHIFT.md) (start-to-finish) · [CLIENT.md](./CLIENT.md) · [SECRETS.md](./SECRETS.md)

Charts from Git, images from a registry with **immutable tags**, secrets via Vault + External Secrets.
