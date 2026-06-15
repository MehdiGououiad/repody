# Air-gapped and regulated deployment

Deploy Repody where production has **no public internet egress**. A **connected staging / CI** host mirrors artifacts into a **private OCI registry**; the regulated zone imports and runs Compose or Kubernetes.

**v1 bundle:** core platform + Grafana/Loki (`obs`) + Bugsink + CPU Repody VLM (Docker Model Runner). GPU/vLLM and Tempo traces are optional add-ons later.

**Secrets:** never included in the release artifact — customer generates all credentials ([`deploy/ENV.md`](../deploy/ENV.md)).

## Architecture

```text
[Internet] ──► [Linux CI / staging] ──► mirror ──► [Internal OCI registry]
        build bundle (images + helm + model)              │
                                                          ▼
                                              [Regulated zone — Compose or K8s]
```

| Phase | Where | Tooling |
|-------|--------|---------|
| Build release | Connected Linux CI | `pnpm airgap:build` |
| Transfer | Customer process | `repody-airgap-X.Y.Z.tar.gz` + `SHA256SUMS` |
| Import | Regulated staging or prod | `pnpm airgap:import` |
| Run | Regulated prod | `pnpm compose` or `helm upgrade` |

## 1. Build a release (vendor / connected CI)

Requires: Linux, Docker, Helm 3, Node 22, pnpm. **Do not run the build on Windows** (use GitHub Actions or a Linux bastion).

```bash
git checkout v0.1.0   # or any tag
pnpm install --frozen-lockfile

# Optional: bake customer DSN into web image at staging rebuild time
export NEXT_PUBLIC_BUGSINK_DSN="http://key@errors.internal.example/1"
export BUGSINK_DSN="$NEXT_PUBLIC_BUGSINK_DSN"

pnpm airgap:build -- --version 0.1.0
```

Output:

```text
dist/airgap/repody-airgap-0.1.0/
  RELEASE.json          # metadata (no secrets)
  MANIFEST.json         # image list
  SHA256SUMS            # integrity v1
  images/*.tar          # docker save archives
  models/               # Repody VLM model or MODEL_INFO.json
  charts/repody-*.tgz   # Helm chart + Bitnami deps
  deploy/               # compose files + pins for offline Compose
dist/airgap/repody-airgap-0.1.0.tar.gz
```

### CI triggers

GitHub Actions workflow [`.github/workflows/airgap-release.yml`](../.github/workflows/airgap-release.yml):

- **`workflow_dispatch`** — test or hotfix bundles (set version input)
- **Git tag `v*`** — formal customer releases (version = tag without `v`)

## 2. Transfer and verify

Copy `repody-airgap-X.Y.Z.tar.gz` to the regulated environment (approved media / one-way import).

```bash
tar -xzf repody-airgap-0.1.0.tar.gz
cd repody-airgap-0.1.0
sha256sum -c SHA256SUMS
```

## 3. Import into internal registry

On a Linux host that can reach your **private registry** (may be inside the regulated zone):

```bash
pnpm airgap:import -- \
  --bundle ./repody-airgap-0.1.0 \
  --registry registry.internal.example.com/repody
```

Without `--registry`, images load into the local Docker daemon only.

### Harbor (reference)

1. Create project `repody` (private).
2. After `airgap:import`, images appear as `registry.internal.example.com/repody/repody-api:0.1.0`, etc.
3. Optional: enable **replication** from a staging Harbor to a production Harbor in a higher trust zone.
4. Map robots / CI accounts with push-only on staging, pull-only on prod.

Equivalent flows work with Artifactory, ECR, ACR — any OCI registry (`docker push` compatible).

## 4. Configure secrets (customer)

Generate locally — **do not** copy vendor `.env` files:

```bash
bash deploy/cloud/setup-env.sh   # interactive template
```

Minimum production variables: see [`deploy/ENV.md`](../deploy/ENV.md) and [DEPLOY.md go-live checklist](../DEPLOY.md#go-live-checklist).

Set image pointers to your internal registry:

```env
REPODY_IMAGE_REGISTRY=registry.internal.example.com/repody/
REPODY_IMAGE_TAG=0.1.0
```

## 5. Deploy — Docker Compose

Use the **bundle’s** compose tree or your git checkout with env above:

```bash
pnpm compose up --stack=prod --with=obs,bugsink --build --detach
```

When images are pre-imported, `--build` skips rebuild if tags exist. Prefer `prod-micro` image layout:

```bash
pnpm compose up --stack=prod-micro --with=obs,bugsink --detach
```

### Repody VLM model (CPU)

If the bundle contains `models/repody-vlm-model.tar`:

```bash
docker load -i models/repody-vlm-model.tar
```

If the bundle contains `models/MODEL_INFO.json`, mirror Hugging Face GGUF to an internal registry, then on the prod host:

```bash
docker model pull <internal>/NuExtract3-GGUF:Q4_K_M
docker model package --from <internal>/nuextract3-gguf:Q4_K_M --context-size 16384 repody/repody-vlm:q4_k_m-16k
```

### TLS

| Pattern | When |
|---------|------|
| **Customer ingress** (recommended) | F5 / nginx / existing ingress terminates TLS; set `AUDIT_CORS_ORIGINS`, `AUDIT_MINIO_PUBLIC_ENDPOINT` |
| **Internal-CA Caddy** | Smaller Compose pilots — mount corporate CA certs; do **not** use Let’s Encrypt in air-gap |

## 6. Deploy — Kubernetes

```bash
helm upgrade --install repody ./charts/repody-0.1.0.tgz \
  -n repody --create-namespace \
  -f my-values.yaml \
  --set secrets.adminApiToken="$(openssl rand -hex 32)" \
  --set images.api.repository=registry.internal.example.com/repody/repody-api \
  --set images.worker.repository=registry.internal.example.com/repody/repody-worker \
  --set images.web.repository=registry.internal.example.com/repody/repody-web \
  --set images.api.tag=0.1.0 \
  --set images.worker.tag=0.1.0 \
  --set images.web.tag=0.1.0
```

**Bitnami subcharts** (Postgres, Redis, MinIO) pull additional images at `helm install` time. Either:

- Mirror Bitnami images to internal registry and set `global.imageRegistry` in values, or
- Disable in-cluster charts and use external managed databases (`postgresql.enabled=false`, etc. — [ADR 004](./adr/004-cloud-kubernetes-packaging.md)).

Point `config.vllmBaseUrl` at an internal vLLM service when you add GPU inference later.

## 7. Observability in regulated zones

| Signal | Component | Notes |
|--------|-----------|-------|
| Platform logs | Loki + Grafana (`--with=obs`) | http://grafana.internal:3001 — change default password |
| Errors | Bugsink (`--with=bugsink`) | Self-hosted; set DSN in env at web **build** time |
| Traces | Tempo (optional v2) | Not in v1 bundle |

## 8. Self-mirror (advanced customers)

Image list SSOT: [`deploy/airgap/manifest.mjs`](../deploy/airgap/manifest.mjs) + [`deploy/pinned-images.env`](../deploy/pinned-images.env).

```bash
node -e "import('./deploy/airgap/manifest.mjs').then(m => console.log(m.airgapImageManifest({tag:'0.1.0'})))"
```

Pull each reference on connected staging, retag, push — same as `airgap:build` but without the full bundle.

## 9. Future modules (not in v1 bundle)

| Module | Add when |
|--------|----------|
| `traces` | Compliance requires distributed tracing |
| `gpu` / vLLM | GPU document extraction — mirror `vllm/vllm-openai` + model weights |
| SBOM / Cosign | Upgrade integrity from checksums-only |

## Related docs

- [DEPLOY.md](../DEPLOY.md) — production checklist
- [BUGSINK.md](./BUGSINK.md) — error tracking setup
- [OBSERVABILITY.md](./OBSERVABILITY.md) — Loki/Grafana
- [CLOUD-K8S.md](./CLOUD-K8S.md) — Helm details
