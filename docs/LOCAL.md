# Local platform (laptop)

Default extraction: **host NuExtract** (`repody:vlm`).  
Cluster / OpenShift: [CLUSTER.md](./CLUSTER.md). Commands: [COMMANDS.md](./COMMANDS.md).

---

## Contributor path

Full checkout for daily work on **Windows · Linux** (`bun run platform`).

### What you get

| Layer                                               | Source                                                                                    |
| --------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| API / UI / workers                                  | Docker Hub (`mehdigououiad/repody-backend` + `repody-web`, `linux/amd64` + `linux/arm64`) |
| Postgres / Hatchet Lite / SeaweedFS (S3) / Keycloak | Docker Compose                                                                            |
| NuExtract `:8081`                                   | Host (**default**)                                                                        |

Images pull as public multi-arch - no Hub login required.

---

## Prerequisites (once)

1. **Docker Desktop** running.
2. **Node 26 (LTS)** + **Bun 1.4.4**:
   ```bash
   npm install --global bun@1.4.4   # the pinned Bun (package.json, packageManager)
   ```
3. **llama-server** on PATH (NuExtract): `winget install ggml.llamacpp` on Windows, or
   [llama.cpp's build](https://github.com/ggml-org/llama.cpp) on Linux. Or skip it and use the
   Modal endpoint ([deploy/modal/README.md](../deploy/modal/README.md)).
4. **NuExtract GGUFs** - download from [numind/NuExtract3-GGUF](https://huggingface.co/numind/NuExtract3-GGUF), set `LLAMACPP_MODEL` + `LLAMACPP_MMPROJ` in `deploy/llamacpp/paths.local.env` ([deploy/llamacpp/README.md](../deploy/llamacpp/README.md)).
5. Disk / RAM for the images (~2–4 GB, plus build cache) and GGUFs.

---

## Install and start

```bash
git clone https://github.com/MehdiGououiad/repody.git
cd repody
bun install
bun run doctor
bun run platform setup             # once: env files + build the images
# edit deploy/llamacpp/paths.local.env with NuExtract GGUF paths
bun run platform doctor            # preflight
bun run platform                   # same preflight, then start
bun run platform status
```

One-shot after clone/install: `bun run platform bootstrap`.

### What `setup` creates (no hand-written secrets)

| File                              | Source                           | Purpose                                         |
| --------------------------------- | -------------------------------- | ----------------------------------------------- |
| `backend/.env`                    | `deploy/env/compose.env.example` | API / Compose / inference URLs                  |
| `.env.local`                      | `deploy/env.auth.example`        | Next.js / Better Auth / Keycloak browser issuer |
| `deploy/llamacpp/paths.local.env` | example                          | **Required** NuExtract GGUF paths               |

Trusted laptop / localhost defaults only - do not expose Compose ports to a LAN or reuse passwords outside development.

### Preflight

```bash
bun run platform doctor
```

Same checks run at the start of `bun run platform`. Required for the default path:

- Node 26 / Bun 1.4
- Docker Desktop running
- `llama-server` on PATH
- NuExtract3 `.gguf` + mmproj on disk
- `backend/.env` + `.env.local`

---

## Sign in and verify

| What       | URL / value                           |
| ---------- | ------------------------------------- |
| UI         | http://localhost:3000                 |
| API health | http://localhost:8000/v1/healthz/live |
| Keycloak   | http://localhost:8080                 |
| User       | `operator@repody.local`               |
| Password   | `repody-dev`                          |

**Use `localhost`, not `127.0.0.1`**, in the browser (OIDC cookie / issuer host must match).

Hub auth: browser issuer `http://localhost:8080/realms/repody`; the web container reads Keycloak's discovery from `AUTH_KEYCLOAK_INTERNAL_ISSUER=http://keycloak:8080/realms/repody`, and Keycloak (`KC_HOSTNAME_BACKCHANNEL_DYNAMIC=true`) answers with server-to-server endpoints on `keycloak:8080`; API JWKS from `http://keycloak:8080/...`.

UI -> API: Next.js proxies `/api/v1/*` at runtime (`INTERNAL_API_URL=http://api:8000` in Compose; Kubernetes sets `http://repody-api:8000`). Same web image on both.

Observability is **on by default** (`--no-obs` to skip):

| UI         | URL                                                         |
| ---------- | ----------------------------------------------------------- |
| Grafana    | http://localhost:3030 (admin / admin)                       |
| Loki       | http://localhost:3100                                       |
| Prometheus | http://localhost:9090                                       |
| Bugsink    | http://localhost:8090 · `admin@repody.local` / `repody-dev` |
| OTLP HTTP  | http://localhost:4318/v1/traces                             |

JSON logs go to Loki; traces to Tempo (`trace_id` links them in Grafana). Config: `deploy/observability/`.

**Bugsink (optional):** create a project -> set `SENTRY_DSN` in `backend/.env` (the API and worker report through the Sentry SDK) and `NEXT_PUBLIC_BUGSINK_DSN` in `.env.local`. Compose passes `BUGSINK_DSN` from the repo-root `.env` to the containers as `SENTRY_DSN`; recreate `api` and `worker` after changing it. Observability starts with `bun run platform` and `bun run platform dev` unless you pass `--no-obs`.

---

## Daily commands

```bash
bun run platform doctor
bun run platform
bun run platform status
bun run platform logs
bun run platform stop
bun run platform help
```

---

## Flags

```bash
bun run platform -- --platform-only
bun run platform -- --no-nuextract
bun run platform -- --no-build
bun run platform -- --no-obs
```

| Flag              | Effect                                            |
| ----------------- | ------------------------------------------------- |
| (default)         | Host NuExtract `:8081` -> `repody:vlm`            |
| `--no-nuextract`  | Skip NuExtract                                    |
| `--platform-only` | Containers only                                   |
| `--no-build`      | Start the images already built (skip the rebuild) |
| `--no-obs`        | Skip Grafana/Bugsink stack                        |

| Catalog      | Pipeline                                       |
| ------------ | ---------------------------------------------- |
| `repody:vlm` | Official NuExtract template JSON (**default**) |

| Command                   | Purpose                       |
| ------------------------- | ----------------------------- |
| `bun run platform setup`  | Once - env + build the images |
| `bun run platform doctor` | Preflight                     |
| `bun run platform`        | Preflight + start             |
| `bun run platform status` | Health                        |
| `bun run platform stop`   | Tear down                     |
| `bun run platform help`   | Flags                         |

---

## Develop from source (contributors)

```bash
bun run platform dev
```

Compose runs Postgres, Hatchet Lite, SeaweedFS (S3) and Keycloak and builds the workers from source; the API
(uvicorn) and UI (next dev) run on the host and reload on edits. Ctrl+C stops API + UI;
`bun run platform stop` stops everything. Flags: `--no-nuextract`, `--no-obs`.

Engineering reference: [DEVELOPMENT.md](./DEVELOPMENT.md).

---

## Troubleshooting

| Symptom                          | Fix                                                                                    |
| -------------------------------- | -------------------------------------------------------------------------------------- |
| `bun run doctor` fails on Docker | Start Docker Desktop; wait until ready                                                 |
| `llama-server` missing           | Install llama.cpp; open a new terminal                                                 |
| Pull slow / timeout              | Retry `bun run platform setup`; check network                                          |
| Wrong arch image                 | Re-pull; confirm the image's arch matches the machine (`linux/amd64` or `linux/arm64`) |
| Login / redirect loops           | Open **http://localhost:3000** (not 127.0.0.1)                                         |
| OCR / NuExtract not ready        | Set GGUF paths; `bun run llamacpp:serve`; `bun run platform status`                    |
| Port in use                      | `bun run platform stop`                                                                |

---

## Related

- Overlay: [`compose.portable.yaml`](../compose.portable.yaml)
- Registry: [`deploy/registry/README.md`](../deploy/registry/README.md)
- Cluster install: [CLUSTER.md](./CLUSTER.md)
- Docs hub: [README.md](./README.md)
