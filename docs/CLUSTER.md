# Cluster and production

> **Status: a reference, tested by hand.** Repody's own hosted demo runs on one VPS with Docker
> Compose ([deploy/vps/README.md](../deploy/vps/README.md)), not on this chart. CI lints the chart
> and validates its manifests (`bun run deploy:check`) but does not install it: before a client
> installation, install it on a local cluster ([Test it locally](#test-it-locally)) and check
> the settings against [deploy/ENV.md](../deploy/ENV.md).

Install Repody on a **Kubernetes or OpenShift** cluster with one Helm chart,
[`deploy/helm/repody`](../deploy/helm/repody). The chart runs the stateless app: API, web, the
Hatchet workers, a migrations Job, and an Ingress. Everything stateful is an external
service the chart points at.

Laptop Compose: [LOCAL.md](./LOCAL.md). Commands: [COMMANDS.md](./COMMANDS.md). Env keys: [deploy/ENV.md](../deploy/ENV.md).

## What the cluster provides

| Service           | Typical choice                                                                                                           | Chart setting                                                                                                                |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------- |
| PostgreSQL        | Managed Postgres, or [CloudNativePG](https://cloudnative-pg.io/) ([examples](../deploy/managed/cloudnativepg/))          | `AUDIT_DATABASE_URL` in the Secret                                                                                           |
| Hatchet           | [Hatchet's Helm chart](https://docs.hatchet.run/self-hosting/kubernetes-quickstart) (on your Postgres), or Hatchet Cloud | `HATCHET_CLIENT_TOKEN` in the Secret; `config.HATCHET_CLIENT_HOST_PORT` when the token's address is not reachable in-cluster |
| S3 object storage | AWS S3, SeaweedFS, Ceph RGW / ODF                                                                                        | `config.AUDIT_S3_ENDPOINT_URL`, keys in the Secret                                                                           |
| OIDC provider     | Keycloak (operator or managed), configured as in [Keycloak in production](#keycloak-in-production)                       | `config.AUDIT_OIDC_ISSUER`, `config.AUDIT_OIDC_AUDIENCE`, `web.keycloakClientId`                                             |
| Document model    | llama-server / vLLM serving NuExtract3 ([EXTRACTION.md](./EXTRACTION.md))                                                | `config.AUDIT_INFERENCE_BASE_URL`                                                                                            |
| Secrets           | External Secrets Operator + Vault                                                                                        | `existingSecret`                                                                                                             |

The pods run with the restricted security context (`runAsNonRoot`, `RuntimeDefault` seccomp,
no capabilities, no pinned UID, read-only root filesystem with `emptyDir` volumes for `/tmp` and
the Next.js cache), which fits Kubernetes PSA **restricted** and OpenShift **restricted-v2**
without a custom SCC.

### Test it locally

With [kind](https://kind.sigs.k8s.io/) and Helm. The services the chart points at can be the
local Compose stack's (`bun run platform dev`), reached from the cluster at `host.docker.internal`:

```bash
kind create cluster --name repody
kubectl create namespace repody
kubectl -n repody create secret generic repody-runtime \
  --from-literal=AUDIT_DATABASE_URL=postgresql+asyncpg://<user>:<password>@host.docker.internal:5432/repody \
  --from-literal=HATCHET_CLIENT_TOKEN=<token> \
  --from-literal=AUDIT_S3_ACCESS_KEY=<key> --from-literal=AUDIT_S3_SECRET_KEY=<secret>
helm install repody deploy/helm/repody -n repody --set existingSecret=repody-runtime \
  --set config.AUDIT_DEPLOYMENT_ENVIRONMENT=development --set ingress.enabled=false
kubectl -n repody get pods -w
```

The migrations Job runs first; then the API, web and workers turn ready. Images come from
`images.*` (a release's `helm-images.yaml` pins their digests). Delete it all with
`kind delete cluster --name repody`.

### Keycloak in production

`deploy/keycloak/realm-repody.json` is the **development** realm: demo users with a shared
password, fixed client secrets and the `repody-e2e` service account. Never import it into a
production Keycloak. Create the realm with:

| Setting             | Value                                                                                                                                                                          |
| ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Realm roles         | `viewer`, `operator`, `admin` (and `platform_admin` if used); assign them to users or groups                                                                                   |
| Client `repody-web` | Confidential; standard flow only (no direct access grants); PKCE `S256`; a generated secret (into the runtime Secret as `AUTH_KEYCLOAK_CLIENT_SECRET`)                         |
| Redirect URI        | Exactly `https://<app host>/api/auth/callback/keycloak` (no wildcards); web origin `+`                                                                                         |
| Scopes              | Full scope off; map the realm roles above to the client (Client scopes → Dedicated scope → Scope) so access tokens carry them                                                  |
| Audience            | An audience mapper adding `repody-api` to access tokens, and `config.AUDIT_OIDC_AUDIENCE: repody-api` (required in production: the API refuses tokens meant for other clients) |
| Hostname            | Keycloak hostname v2 with `KC_HOSTNAME` set to its public URL; when the web pods reach it in-cluster (`web.internalIssuer`), also `KC_HOSTNAME_BACKCHANNEL_DYNAMIC=true`       |

| Client groups | One group `client-<name>` per client company when several share the installation (their users see only its work); a single-client installation needs none |
| Groups in tokens | A Group Membership mapper on `repody-web`: token claim `groups`, full group path off, in the access token |
| Admin area (optional) | Client `repody-admin`: confidential, service accounts only (no standard flow, no direct grants), full scope off. Its service account gets realm-management's `manage-users`, `view-users`, `query-users`, `query-groups`; map those four to the client's scope (Client scopes → Dedicated scope → Scope), and add the client scope `kc-admin-api` as a default scope (Keycloak 26.8.2+ refuses Admin API tokens without it). Its secret goes into the runtime Secret as `KEYCLOAK_ADMIN_CLIENT_SECRET`. The steps as `kcadm.sh` commands: [`deploy/keycloak/setup-admin-client.sh`](../deploy/keycloak/setup-admin-client.sh) |

The API accepts only access tokens (`typ: Bearer`) signed by the realm, for that audience.
The e2e tests' service account (`repody-e2e`, client credentials, operator role) belongs only in
a test realm.

## Install

### 1. Namespace

```bash
kubectl apply -f deploy/client/namespace.example.yaml
```

### 2. Runtime Secret

Create `repody-runtime-secrets` (the chart's `existingSecret`) from your secret manager - the
ExternalSecret example is [`deploy/client/secrets/runtime.externalsecret.example.yaml`](../deploy/client/secrets/runtime.externalsecret.example.yaml).

| Key                                          | Used by                                                               |
| -------------------------------------------- | --------------------------------------------------------------------- |
| `AUDIT_DATABASE_URL`                         | API, workers, migrations (`postgresql+asyncpg://…`)                   |
| `HATCHET_CLIENT_TOKEN`                       | API, workers (a Hatchet API token: dashboard → Settings → API Tokens) |
| `AUDIT_S3_ACCESS_KEY`, `AUDIT_S3_SECRET_KEY` | API, workers                                                          |
| `AUTH_SECRET`                                | web (Better Auth session encryption, as `BETTER_AUTH_SECRET`)         |
| `AUTH_KEYCLOAK_CLIENT_SECRET`                | web (Keycloak confidential client)                                    |
| `AUDIT_INFERENCE_API_KEY`                    | workers, optional bearer token for the inference endpoint             |
| `BUGSINK_DSN`                                | optional error tracking                                               |
| `KEYCLOAK_ADMIN_CLIENT_SECRET`               | API, optional: the admin area's Keycloak account (`repody-admin`)     |

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
- **Inference:** `AUDIT_INFERENCE_BASE_URL` must be reachable from the workers - never `host.docker.internal`.
- **NetworkPolicy:** off by default (platform teams usually own it). `networkPolicy.enabled: true` gives a default-deny policy that allows in-release traffic, DNS, ingress to web/API, and egress to `networkPolicy.egressCidrs`.

## Images and releases

```bash
REPODY_IMAGE_REGISTRY=ghcr.io/yourorg REPODY_IMAGE_TAG=1.2.3 bun run images:release
```

Tags must be immutable (`docker-bake.hcl` rejects empty and `latest`). In CI, each master
commit's images are built by [`images-ghcr.yml`](../.github/workflows/images-ghcr.yml) with
BuildKit SBOM and provenance attestations, and their digests are signed with cosign (keyless). A
release tag `v1.2.3` promotes that build, by digest, as `1.2.3`
([`release.yml`](../.github/workflows/release.yml)), and uploads `helm-images.yaml` with the
digests to pin in values. Before a client handoff,
[`release-promote.yml`](../.github/workflows/release-promote.yml) verifies that master's build
signed them:

```bash
cosign verify ghcr.io/yourorg/repody-backend:1.2.3 --certificate-oidc-issuer https://token.actions.githubusercontent.com --certificate-identity 'https://github.com/yourorg/repody/.github/workflows/images-ghcr.yml@refs/heads/master'
```

Registry notes (GHCR, Harbor, other OCI registries): [deploy/registry/README.md](../deploy/registry/README.md).

## Observability

The chart ships no logging stack: Repody speaks the open standards, and the cluster's own tools
collect them (OpenShift logging, Elastic, Splunk, Datadog, Grafana Loki, …).

| Signal | What Repody emits                                                                                                                                                                                                                  | How the cluster collects it                                                                                                                                                                                 |
| ------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Logs   | One JSON object per line on stdout (`AUDIT_LOG_JSON=true`): `level`, `event`, `timestamp`, the ids it concerns (`run_id`, `workflow_id`, `account`) and the request's `trace_id`. Never a document's content or an extracted value | The cluster's node agent (Fluent Bit, the OpenTelemetry Collector, Grafana Alloy) reads container stdout like any pod's                                                                                     |
| Errors | Exceptions with their stack trace, through the Sentry SDK, when `BUGSINK_DSN` is in the Secret (API, workers and web)                                                                                                              | Any Sentry-compatible server: [Bugsink](https://www.bugsink.com/) (Repody's own, PolyForm Shield license), [GlitchTip](https://glitchtip.com/) (MIT) or Sentry. Events carry the image tag as their release |
| Traces | OTLP, when `OTEL_SDK_DISABLED=false` and `OTEL_EXPORTER_OTLP_ENDPOINT` is set                                                                                                                                                      | An OpenTelemetry Collector (for example its [Helm chart](https://github.com/open-telemetry/opentelemetry-helm-charts/tree/main/charts/opentelemetry-collector)) and any trace backend                       |

The Compose profiles of `deploy/vps` (Loki, Alloy, Grafana, Bugsink) are for a single server whose
containers log to journald; they have no role on Kubernetes.

### Timeouts (extract pool)

| Env var                                         | Default | Rule                                                              |
| ----------------------------------------------- | ------- | ----------------------------------------------------------------- |
| `AUDIT_RUN_TIMEOUT_MINUTES`                     | 5       | Hatchet's execution timeout: a longer run is cancelled and failed |
| `AUDIT_INFERENCE_TIMEOUT_SECONDS`               | 180     | Per model call, ≤ run timeout (checked at start)                  |
| `workers.extract.terminationGracePeriodSeconds` | 240     | ≥ worker timeout in seconds                                       |

### Connection budget

Defaults: `AUDIT_DB_POOL_SIZE=10`, `AUDIT_WORKER_CONCURRENCY=1` (runs per worker pod).

```
Postgres connections ≈ (api + worker replicas) × (pool size + overflow)
```

Lower the pool settings when Postgres `max_connections` is tight (or put PgBouncer / the CNPG Pooler in front).

### Health and alerts

- `GET /v1/healthz/live` - liveness; `GET /v1/healthz` - readiness (Postgres).
- Workers: a liveness probe on the Hatchet SDK's `/health` (port 8001). When a worker stops, Hatchet fails its runs through the workflow's failure task. Hatchet's dashboard shows workers, runs and the cron.

| Alert               | Log event / signal                                         | Threshold                   |
| ------------------- | ---------------------------------------------------------- | --------------------------- |
| Run failures        | `run_failed`                                               | >5% of runs / 15m           |
| Hatchet unreachable | `run_dispatch_failed` (the run fails; the API answers 503) | any                         |
| Queue pressure      | dashboard `queue.queuedRuns` vs `AUDIT_MAX_QUEUED_RUNS`    | >80% for 10m                |
| Slow model          | run metadata `extractionMs`                                | p99 > 80% of worker timeout |
| Worker crash loop   | `repody-worker` restarts                                   | >3 / 15m                    |

## Troubleshooting

| Symptom                           | Check                                                                                                                                                                                     |
| --------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Pods `CreateContainerConfigError` | `repody-runtime-secrets` exists and has the keys above                                                                                                                                    |
| Migrations Job fails              | `AUDIT_DATABASE_URL` reachable from the namespace                                                                                                                                         |
| Workers cannot extract            | `AUDIT_INFERENCE_BASE_URL` reachable; 401 means `AUDIT_INFERENCE_API_KEY`                                                                                                                 |
| Upload fails                      | `AUDIT_MAX_UPLOAD_BYTES` and the Ingress body size limit                                                                                                                                  |
| Sign-in loops / 401               | Issuer and JWKS reachable from API and web pods (`web.internalIssuer`)                                                                                                                    |
| `ImagePullBackOff`                | Pull secret; repository includes the registry host                                                                                                                                        |
| Run waits `queued`                | Hatchet's dashboard: workers connected, the client's rate limit and round robin (`AUDIT_RUNS_PER_MINUTE_PER_CLIENT`, `AUDIT_RUNS_IN_PROGRESS_PER_CLIENT`); after an hour Hatchet fails it |
| Run long `running`                | Worker logs; model endpoint; Hatchet fails it after `AUDIT_RUN_TIMEOUT_MINUTES`                                                                                                           |
| Progress not updating             | The worker is running and reaches Postgres; `GET /api/v1/runs/{id}` answers                                                                                                               |
