# Development workflow

Local development and production-path testing use **Kubernetes only** (kind + Helm + Gateway API). See [DEPLOY.md](./DEPLOY.md) for staging and production clusters.

## Prerequisites

- Docker Desktop (kind + Harbor)
- Node 22+, pnpm 10+
- `kind`, `kubectl`, `helm` on PATH

## Quick start

```powershell
pnpm install
pnpm harbor:bootstrap    # once — local Harbor registry
pnpm k8s:local:hosts     # once — admin; maps *.repody.local → 127.0.0.1
pnpm registry:warm       # once — cache third-party images in Harbor
pnpm dev                 # bootstrap Helm stack (first time or after pnpm stop)
pnpm dev:sync            # daily loop — Skaffold hot sync (Python/TS)
```

| URL | Service |
|-----|---------|
| http://app.repody.local | Web (Gateway) |
| http://api.repody.local | API |
| http://auth.repody.local | Keycloak |
| http://grafana.repody.local | Grafana (admin / audit) — `pnpm dev:full` only |

Sign in: `operator@repody.local` / `repody-dev`

**Stop app (keep cluster):** `pnpm stop` — **tear down cluster:** `pnpm stop:cluster` or `pnpm platform:reset`

## Commands

| Goal | Command |
|------|---------|
| **Bootstrap stack** | `pnpm dev` — once per session or after `pnpm stop` |
| **Daily code loop** | `pnpm dev:sync` — Skaffold sync (primary inner loop) |
| **Force image rebuild** | `pnpm dev:build` |
| **Fast redeploy** (skip waits) | `pnpm dev:fast` |
| **Warm third-party images** | `pnpm registry:warm` — after clone; avoids Docker Hub pulls |
| **Stop app only** | `pnpm stop` — keeps kind + Harbor (fast `pnpm dev` next time) |
| **Stop cluster** | `pnpm stop:cluster` — Harbor keeps running (`pnpm harbor:down` to stop) |
| Full stack (Argo + Grafana) | `pnpm dev:full` |
| Wipe data + cluster + Harbor | `pnpm platform:reset` (add `--keep-harbor` to retain registry) |

Advanced flags (same script): `pnpm k8s:local -- --minimal --build --logs`

## External inference

Point workers at an OpenAI-compatible VLM endpoint (chart does not run inference):

```powershell
$env:REPODY_VLLM_BASE_URL="https://your-vlm-host/v1"
$env:REPODY_VLLM_SERVED_MODEL="your-model"
$env:REPODY_VLLM_API_KEY="optional-key"
pnpm k8s:local
```

See [deploy/llamacpp/README.md](./deploy/llamacpp/README.md) and [docs/REPODY-VLM.md](./docs/REPODY-VLM.md).

## Code changes

| Change | Action |
|--------|--------|
| Next.js / React | `pnpm dev:sync` (Skaffold) or `pnpm dev:build` when Dockerfile/deps change |
| Python API / workers | `pnpm dev:sync` — default daily loop |
| Helm values / `AUDIT_*` env only | `pnpm dev:fast` |
| Docker/pyproject change | `pnpm dev` or `pnpm dev:build` |
| Host llama-server (`deploy/llamacpp/*.local.env`) | Restart `pnpm llamacpp:serve` / `pnpm llamacpp:surya:serve` on the host |

### Local deploy speed

| Scenario | Typical time |
|----------|----------------|
| **Warm re-run** (`pnpm dev`, cluster up, no code change) | **~30s** — skips build, push, Helm |
| **After `pnpm stop`** (Helm removed, kind kept) | **~2–4 min** — no image rebuild if tags unchanged |
| **First clone** (`registry:warm` + first `pnpm dev`) | **~8–15 min** — third-party pulls + image build |
| **Daily code loop** | **`pnpm dev:sync`** — seconds per save (Skaffold sync) |

- **Soft stop** — `pnpm stop` uninstalls Helm only; kind + Harbor stay up
- **Skaffold inner loop** — `pnpm dev:sync` after first `pnpm dev`; no rebuild/re-helm per save
- **Registry warm** — `pnpm registry:warm` once; third-party images skip pull when already in Harbor
- **Content-hash tags** — `pnpm dev` rebuilds only when sources change; `pnpm dev:build` to force
- **BuildKit cache** — `.docker-cache/` speeds repeat image builds
- **Parallel bootstrap** — Docker builds run while kind + Envoy Gateway install
- **Force Helm** — `pnpm k8s:local -- --deploy` when values changed but image tags did not

- **One backend image** (`repody-backend`) — api and workers share a single build; role is chosen by Kubernetes command
- **Content-hash tags** — rebuild when source changes, not only on git commit
- **Selective builds** — frontend-only edits skip backend Docker builds
- **Skaffold sync** (`pnpm dev:sync`) — copy `.py` into running pods; API uses `uvicorn --reload`
- **BuildKit registry cache** — CI reuses layers via GHCR `repody-backend:buildcache`
- **`--fast`** — skip long readiness waits when pods are already healthy
- **`--minimal`** — skip Argo CD + Grafana/Loki stack
- **Single Helm apply** — no web pod restart every run for Keycloak hostAlias
- **Helm migration hook** — migrations run once per upgrade, not on every API start

### Why api, worker, and OCR extras exist

Repody splits **process roles**, not Python packages:

| Piece | What it is | Why separate from inference |
|-------|------------|------------------------------|
| **`repody-api`** | HTTP control plane (auth, uploads, dispatch) | Serves browsers and integrations; scales on request traffic |
| **`repody-worker-*`** | Hatchet job runners (extraction, rules) | Long-running document jobs; scale independently of API |
| **Host inference** (llama-server) | GPU/CPU model weights + token generation | Operated outside the chart ([ADR 005](./docs/adr/005-kubernetes-only-external-inference.md)) |
| **`ocr` Python extra** (`surya-ocr` package) | **Client library** in the worker — layout, env, HTTP calls to llama-server | Not the model. Inference stays on llama-server; the worker orchestrates pages and assembles markdown |

So: **inference runs on llama-server**; **workers run orchestration code** that may import `surya-ocr` to drive that endpoint. Repody VLM is similar — the worker calls your OpenAI-compatible URL; it does not embed NuExtract weights.

We used to build `repody-api` without `ocr` to keep the API image smaller. In practice only workers need Surya, but both roles share one codebase, so we now ship **one `repody-backend` image** (with `otel,ocr` extras) and pick the process via Helm `command` — one Docker build locally, same digest in production.

**Settings → Models → Model runtime configuration** lists every effective knob per model, the env var that sets it, and whether you need a worker restart, API restart, or host inference restart.

### What belongs where

| Layer | Examples | How to change |
|-------|----------|---------------|
| **Host inference** | llama-server port, `--parallel`, GPU layers, GGUF paths | `deploy/llamacpp/paths.local.env` or `surya-paths.local.env` |
| **Platform env (`AUDIT_*`)** | `AUDIT_SURYA_IMAGE_DPI`, `AUDIT_REPODY_VLM_PDF_DPI`, inference URLs | Helm `values-local.yaml` / ConfigMap → `kubectl rollout restart` workers |
| **Worker Python code** | Preprocessing, cache logic, Surya client wiring | `pnpm dev:sync` or rebuild `repody-backend` |

Surya **`IMAGE_DPI`** is **not** llama-server config. The worker sets it in the Surya Python process before calling your host llama-server. Only model weights, slots, and server flags live on llama-server.

Config-only example (no image rebuild):

```powershell
# Edit deploy/helm/repody/values-local.yaml (suryaImageDpi, repodyVlmPdfDpi, …)
pnpm k8s:local:deploy
```

Worker rollout without full rebuild (cluster already up):

```powershell
kubectl rollout restart deployment -n repody -l app.kubernetes.io/component=worker-ocr
kubectl rollout restart deployment -n repody -l app.kubernetes.io/component=worker-fast
```

## Logs and observability

Tail **all running pods** after bootstrap (api, workers, web, Hatchet, Keycloak, Postgres, Redis, MinIO, Envoy gateway, and Argo CD when not using `--minimal`):

```powershell
pnpm k8s:local -- --minimal --logs
```

Or follow logs manually once the stack is up:

```powershell
kubectl -n repody get pods
kubectl -n repody logs -f <pod-name> --all-containers=true --prefix=true
```

Grafana: http://grafana.repody.local (after `pnpm k8s:local:hosts`)

## Tests

```powershell
pnpm test:api              # unit (Postgres service in CI)
pnpm test:e2e:smoke        # Playwright (stack must be up)
pnpm k8s:local:smoke       # full platform smoke via Gateway
```

E2E against the local cluster: [docs/E2E.md](./docs/E2E.md)

## Troubleshooting `pnpm k8s:local`

| Symptom | Fix |
|---------|-----|
| `Docker is not running` | Start Docker Desktop |
| `UPGRADE FAILED` / ConfigMap or Job conflict | `pnpm k8s:local:reset` then retry |
| Image build fails (`uv pip` timeout) | Retry, or run without `--build` if images exist |
| No logs yet | `--logs` starts only **after** bootstrap succeeds (can take 10–20 min on first run) |
| Helm/web rollout stuck | `pnpm k8s:local:reset` |

Use `pnpm dev` for daily work. Use `pnpm dev:full` only when you need Grafana/Argo CD. First bootstrap still takes 10–20 minutes; redeploys should be much faster.
