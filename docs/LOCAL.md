# Run Repody on a laptop

`bun run platform` builds the images from your checkout and starts the whole product with
Docker Compose. The model (NuExtract3) runs on the host with llama-server. It works on Windows
and Linux. Every command: [COMMANDS.md](./COMMANDS.md).

## What runs where

| Part                                             | Where                                                                    |
| ------------------------------------------------ | ------------------------------------------------------------------------ |
| API, web app, worker                             | Containers built from this checkout (`repody-*:dev`, cached)             |
| Postgres, Hatchet Lite, SeaweedFS (S3), Keycloak | Containers ([`compose.yaml`](../compose.yaml))                           |
| Logs and errors: Grafana, Loki, Tempo, Bugsink   | Containers, on by default (`--no-obs` skips them)                        |
| NuExtract3 on `:8081`                            | The host: llama-server ([deploy/llamacpp](../deploy/llamacpp/README.md)) |

## Prerequisites (once)

1. **Docker Desktop**, running.
2. **Node 26** and **Bun 1.4.4**: `npm install --global bun@1.4.4`.
3. **llama-server** on `PATH`: `winget install ggml.llamacpp` on Windows, or
   [llama.cpp's build](https://github.com/ggml-org/llama.cpp) on Linux.
4. **The NuExtract3 GGUF files**: `bun run llamacpp:download` (needs the Hugging Face CLI), or
   download them from [numind/NuExtract3-GGUF](https://huggingface.co/numind/NuExtract3-GGUF).
   Then set `LLAMACPP_MODEL` and `LLAMACPP_MMPROJ` in `deploy/llamacpp/paths.local.env`.

`bun run platform` always sends extraction to `:8081` on the host: it rewrites
`AUDIT_INFERENCE_BASE_URL` in `backend/.env` at each start, and the containers reach the host at
`host.docker.internal:8081`. No GPU here? Run llama-server on another machine and forward its
port to the host's `:8081` (for example `ssh -L 8081:localhost:8081 gpu-box`), then start with
`--no-nuextract`. Without a model, everything but extraction works.

## Start

```bash
bun install
bun run platform setup    # once: writes the env files, builds the images
bun run platform          # checks everything (doctor), then starts the stack and the model
bun run platform status
```

`setup` writes these files from templates, with local-only passwords:

| File                              | From                             | Holds                               |
| --------------------------------- | -------------------------------- | ----------------------------------- |
| `backend/.env`                    | `deploy/env/compose.env.example` | API, Compose and model settings     |
| `.env.local`                      | `deploy/env.auth.example`        | The web app's sign-in (Better Auth) |
| `deploy/llamacpp/paths.local.env` | its `.example`                   | Where the GGUF files are            |

These defaults are for a trusted laptop only: do not expose the Compose ports to a network.

## Sign in

| What       | Where                                                         |
| ---------- | ------------------------------------------------------------- |
| Web app    | http://localhost:3000, `operator@repody.local` / `repody-dev` |
| API health | http://localhost:8000/v1/healthz/live                         |
| Keycloak   | http://localhost:8080 (`admin` / `admin`)                     |
| Hatchet    | http://localhost:8888 (`admin@example.com` / `Admin123!!`)    |
| Grafana    | http://localhost:3030                                         |
| Bugsink    | http://localhost:8090, `admin@repody.local` / `repody-dev`    |

Use **`localhost`, not `127.0.0.1`**, in the browser: the sign-in cookies are tied to the host
name.

The web app reaches the API through its own `/api/v1/*` proxy (`INTERNAL_API_URL`), and the
API checks tokens against Keycloak on the Compose network, so the same images run in Compose
and on a cluster.

To report errors to the local Bugsink, create a project there, set its DSN as `BUGSINK_DSN` in
`backend/.env`, and run `bun run platform` again.

## Work on the code

```bash
bun run platform dev
```

Compose runs the data services and the worker. The API (uvicorn) and the web app (`next dev`)
run on the host and reload when you edit them. Ctrl+C stops those two;
`bun run platform stop` stops everything. Tests, layout and conventions:
[DEVELOPMENT.md](./DEVELOPMENT.md).

## Options

| Option            | Effect                                              |
| ----------------- | --------------------------------------------------- |
| `--no-nuextract`  | Do not start the host model (use a remote endpoint) |
| `--platform-only` | Containers only, no host model                      |
| `--no-obs`        | Skip Grafana, Loki, Tempo and Bugsink               |
| `--no-build`      | Start the images already built                      |

Pass them after `--`: `bun run platform -- --no-obs`.

To run a published release instead of your checkout, set `REPODY_BACKEND_IMAGE` and
`REPODY_WEB_IMAGE` to its images (GHCR, after `docker login ghcr.io`:
[deploy/registry/README.md](../deploy/registry/README.md)).

## Troubleshooting

| Symptom                         | Fix                                                                      |
| ------------------------------- | ------------------------------------------------------------------------ |
| `bun run platform doctor` fails | It says what is missing; start Docker Desktop and wait until it is ready |
| `llama-server` not found        | Install llama.cpp, then open a new terminal                              |
| The model is not ready          | Check the GGUF paths, then `bun run llamacpp:verify`                     |
| Sign-in loops or redirects      | Open http://localhost:3000, not 127.0.0.1                                |
| After recreating Keycloak       | Sign out and in again, or clear the `localhost` cookies                  |
| A port is in use                | `bun run platform stop`                                                  |
