# Cluster and production

Install Repody on a **Kubernetes or OpenShift** cluster with one Helm chart,
[`deploy/helm/repody`](../deploy/helm/repody). The chart runs the stateless app: API, web, the
two Taskiq worker pools, a migrations Job, and an Ingress. Everything stateful is an external
service the chart points at.

Laptop Compose: [LOCAL.md](./LOCAL.md). Commands: [COMMANDS.md](./COMMANDS.md). Env keys: [deploy/ENV.md](../deploy/ENV.md).

## What the cluster provides

| Service | Typical choice | Chart setting |
|---------|----------------|---------------|
| PostgreSQL | Managed Postgres, or [CloudNativePG](https://cloudnative-pg.io/) ([examples](../deploy/managed/cloudnativepg/)) | `AUDIT_DATABASE_URL` in the Secret |
| Redis | Managed Redis/Valkey, or an operator | `AUDIT_REDIS_URL` in the Secret |
| S3 object storage | S3, MinIO operator, ODF | `config.AUDIT_S3_ENDPOINT_URL`, keys in the Secret |
| OIDC provider | Keycloak (operator or managed), realm [`deploy/keycloak/realm-repody.json`](../deploy/keycloak/realm-repody.json) | `config.AUDIT_OIDC_ISSUER`, `web.keycloakClientId` |
| Document model | llama-server / vLLM serving NuExtract3 ([EXTRACTION.md](./EXTRACTION.md)) | `config.AUDIT_LLAMACPP_BASE_URL` |
| Secrets | External Secrets Operator + Vault | `existingSecret` |

The pods run with the restricted security context (`runAsNonRoot`, `RuntimeDefault` seccomp,
no capabilities, no pinned UID), which fits Kubernetes PSA **restricted** and OpenShift
**restricted-v2** without a custom SCC.

## Install

### 1. Namespace

```bash
kubectl apply -f deploy/client/namespace.example.yaml
```

### 2. Runtime Secret

Create `repody-runtime-secrets` (the chart's `existingSecret`) from your secret manager - the
ExternalSecret example is [`deploy/client/secrets/runtime.externalsecret.example.yaml`](../deploy/client/secrets/runtime.externalsecret.example.yaml).

| Key | Used by |
|-----|---------|
| `AUDIT_DATABASE_URL` | API, workers, migrations (`postgresql+asyncpg://…`) |
| `AUDIT_REDIS_URL` | API, workers |
| `AUDIT_S3_ACCESS_KEY`, `AUDIT_S3_SECRET_KEY` | API, workers |
| `AUTH_SECRET` | web (Auth.js session encryption) |
| `AUTH_KEYCLOAK_CLIENT_SECRET` | web (Keycloak confidential client) |
| `AUDIT_LLAMACPP_API_KEY` | workers, optional bearer token for the inference endpoint |
| `BUGSINK_DSN` | optional error tracking |

The image pull secret comes from [`registry-pull.externalsecret.example.yaml`](../deploy/client/secrets/registry-pull.externalsecret.example.yaml).

### 3. Values

Copy [`values-production.yaml.example`](../deploy/helm/repody/values-production.yaml.example)
to a private GitOps repo and fill in images, hosts and `config.*`. `config` is rendered into
the ConfigMap as-is, so its keys are the `AUDIT_*` names from [deploy/ENV.md](../deploy/ENV.md).

### 4. Helm install

```bash
helm upgrade --install repody deploy/helm/repody -n repody -f values-production.yaml --wait --timeout 15m
```

The migrations Job runs `alembic upgrade head` as a pre-install/pre-upgrade hook.
GitOps: [`deploy/client/argocd.application.yaml`](../deploy/client/argocd.application.yaml) (chart from the vendor tag, values from the client repo).

### 5. Verify

```bash
kubectl -n repody get pods
```

```bash
curl -fsS https://api.example.com/v1/healthz
```

Then sign in on the app host and run a test extraction from the workflow builder.

## How the pieces connect

- **Web to API:** the web pod gets `INTERNAL_API_URL=http://<release>-api:8000`; Next.js proxies browser `/api/v1/*` there, so the same image works on Compose and Kubernetes.
- **OIDC:** browsers use `AUDIT_OIDC_ISSUER` (public URL). If pods cannot reach that URL, set `web.internalIssuer` and `config.AUDIT_OIDC_JWKS_URL` to the in-cluster Keycloak Service.
- **Uploads:** files go to the API in the run request (multipart), and the API stores them in S3; only the API and workers reach the bucket.
- **Inference:** `AUDIT_LLAMACPP_BASE_URL` must be reachable from the workers - never `host.docker.internal`.
- **NetworkPolicy:** off by default (platform teams usually own it). `networkPolicy.enabled: true` gives a default-deny policy that allows in-release traffic, DNS, ingress to web/API, and egress to `networkPolicy.egressCidrs`.

## Images and releases

```bash
REPODY_IMAGE_REGISTRY=ghcr.io/yourorg REPODY_IMAGE_TAG=1.2.3 pnpm images:release
```

Tags must be immutable (`docker-bake.hcl` rejects empty and `latest`). In CI,
[`images-ghcr.yml`](../.github/workflows/images-ghcr.yml) builds both images with BuildKit SBOM
and provenance attestations, signs the digests with cosign (keyless), and uploads
`helm-images.yaml` with the digests to pin in values. Before a client handoff,
[`release-promote.yml`](../.github/workflows/release-promote.yml) verifies the signatures:

```bash
cosign verify ghcr.io/yourorg/repody-backend:1.2.3 --certificate-oidc-issuer https://token.actions.githubusercontent.com --certificate-identity-regexp '^https://github.com/yourorg/repody/.github/workflows/images-ghcr.yml@'
```

Registry notes (GHCR, Docker Hub, Harbor): [deploy/registry/README.md](../deploy/registry/README.md).

## Observability

Repody writes JSON logs (`AUDIT_LOG_JSON`) and optional OTLP traces
(the OpenTelemetry agent runs when `OTEL_SDK_DISABLED=false`; set `OTEL_EXPORTER_OTLP_ENDPOINT`). Bring your own collector and backends -
for example the [OpenTelemetry Collector chart](https://github.com/open-telemetry/opentelemetry-helm-charts/tree/main/charts/opentelemetry-collector)
with Grafana, Loki and Tempo. `BUGSINK_DSN` in the Secret enables error tracking.

### Timeouts (extract pool)

| Env var | Default | Rule |
|---------|---------|------|
| `AUDIT_RUN_TIMEOUT_MINUTES` | 5 | A longer run fails; maintenance fails a `running` run past it |
| `AUDIT_INFERENCE_TIMEOUT_SECONDS` | 180 | Per model call, ≤ run timeout (checked at start) |
| `workers.extract.terminationGracePeriodSeconds` | 240 | ≥ worker timeout in seconds |

### Connection budget

Defaults: `AUDIT_DB_POOL_SIZE=10`, `AUDIT_WORKER_CONCURRENCY=1` (runs per worker pod).

```
Postgres connections ≈ (api + worker replicas) × (pool size + overflow)
Redis connections    ≈ (api + worker replicas) × redis max connections
```

Lower the pool settings when Postgres `max_connections` is tight (or put PgBouncer / the CNPG Pooler in front).

### Health and alerts

- `GET /v1/healthz/live` - liveness; `GET /v1/healthz` - readiness (Postgres + Redis).
- Workers have no probe: Taskiq redelivers a task whose worker stopped, and maintenance fails runs that stay `running`.

| Alert | Log event / signal | Threshold |
|-------|--------------------|-----------|
| Run failures | `run_failed` | >5% of runs / 15m |
| Stuck runs reaped | `stale_run_reaped` | any |
| Dispatch failure | `taskiq_dispatch_failed` (run stays queued; maintenance re-sends) | sustained |
| Queue pressure | dashboard `queue.queuedRuns` vs `AUDIT_MAX_QUEUED_RUNS` | >80% for 10m |
| Slow model | run metadata `extractionMs` | p99 > 80% of worker timeout |
| Worker crash loop | `repody-worker` restarts | >3 / 15m |

## Troubleshooting

| Symptom | Check |
|---------|-------|
| Pods `CreateContainerConfigError` | `repody-runtime-secrets` exists and has the keys above |
| Migrations Job fails | `AUDIT_DATABASE_URL` reachable from the namespace |
| Workers cannot extract | `AUDIT_LLAMACPP_BASE_URL` reachable; 401 means `AUDIT_LLAMACPP_API_KEY` |
| Upload fails | `AUDIT_MAX_UPLOAD_BYTES` and the Ingress body size limit |
| Sign-in loops / 401 | Issuer and JWKS reachable from API and web pods (`web.internalIssuer`) |
| `ImagePullBackOff` | Pull secret; repository includes the registry host |
| Run stuck `queued` | Redis; worker replicas; `runs.dispatched_at` NULL means not yet sent |
| Run stuck `running` | Worker logs; model endpoint; maintenance fails it after `AUDIT_RUN_TIMEOUT_MINUTES` |
| Progress not live (SSE) | Redis reachable (`redisOk` in readiness); proxy buffering off for `/api/v1/runs/*/events` |
