# Repody Mac runtime (no source code)

Ship this folder (or the zip from `pnpm client:pack:mac`) to Mac users.  
They **pull Docker images** and run Compose - they never get `backend/`, `app/`, or the git repo.

| Layer | What they get |
|-------|----------------|
| API / UI / workers | Docker Hub `mehdigououiad/repody-backend` + `repody-web` (`linux/arm64`) |
| Postgres / Redis / MinIO / Keycloak | Public images via Compose |
| NuExtract | Host `llama-server` + GGUFs (not in the zip) |

---

## Prerequisites

1. **Docker Desktop** for Mac (Apple Silicon OK).
2. **llama.cpp**: `brew install llama.cpp`
3. **NuExtract3 GGUFs** from [numind/NuExtract3-GGUF](https://huggingface.co/numind/NuExtract3-GGUF) (weights + `mmproj-NuExtract3-BF16.gguf`).

---

## Install

```bash
# unzip the vendor package, then:
cd repody-mac-runtime
chmod +x bin/repody
./bin/repody setup
# edit models/paths.env → LLAMACPP_MODEL + LLAMACPP_MMPROJ (absolute paths)
./bin/repody doctor
./bin/repody start
```

Open **http://localhost:3000** (not `127.0.0.1`).

| | |
|--|--|
| User | `operator@repody.local` |
| Password | `repody-dev` |

---

## Daily commands

```bash
./bin/repody doctor
./bin/repody start
./bin/repody status
./bin/repody stop
./bin/repody pull          # refresh Hub images when vendor publishes a new tag
```

Update image tags in `.env` (`REPODY_BACKEND_IMAGE` / `REPODY_WEB_IMAGE`) when the vendor gives you a new release.

---

## What is not included (by design)

- Application source (Python / Next.js)
- Build toolchains (`pnpm`, `uv`, Docker build of the app)
- Model weights (download separately; license/size)

This kit is **runtime + config only**.

---

## Vendor: build the zip

From the private monorepo:

```bash
pnpm client:pack:mac
# → dist/repody-mac-runtime-<tag>.zip
```

Hand the zip + image tag to the client. Keep the git repo private.

Cluster / OpenShift clients use Helm (`deploy/client/`) instead - see docs/CLUSTER.md.
