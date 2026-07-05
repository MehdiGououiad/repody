# Deploy documentation

**Canonical index.** Manifests and Helm charts live under [`deploy/`](../../deploy/).

## Four deployment paths

| Path | Audience | Guide | Entry command |
|------|----------|-------|---------------|
| **Local dev** | Developers | [LOCAL.md](./LOCAL.md) | `pnpm dev:all` |
| **Client external** | Production — BYO Postgres/Redis/S3 | [CLIENT.md](./CLIENT.md#external-profile-byo-services) · [VENDOR-TO-CLIENT.md](./VENDOR-TO-CLIENT.md) | Helm / Argo CD |
| **Client bundled** | Production — in-cluster data plane | [CLIENT.md](./CLIENT.md#bundled-profile-in-cluster-data-plane) · [VENDOR-TO-CLIENT.md](./VENDOR-TO-CLIENT.md) | Helm / Argo CD |
| **Vendor release** | Ship images to GHCR / client registry | [VENDOR-TO-CLIENT.md](./VENDOR-TO-CLIENT.md) · [RELEASE.md](./RELEASE.md) | `pnpm images:release` |

Command cheat sheet: [docs/COMMANDS.md](../COMMANDS.md).

---

## Vendor → client in 7 steps

1. **Vendor:** `docker login` + `pnpm images:release` with `REPODY_IMAGE_REGISTRY=ghcr.io/yourorg/repody` (or client registry)
2. **Vendor:** Hand off tag, charts, and [deploy/client/](../../deploy/client/) templates
3. **Client:** Namespace + Vault + ESO ([SECRETS.md](./SECRETS.md))
4. **Client:** Store `REGISTRY_DOCKERCONFIGJSON` in Vault → `registry-pull-secret`
5. **Client:** Copy `values-{external,bundled}.example.yaml` to private GitOps repo
6. **Client:** `helm upgrade --install` (data chart first if bundled)
7. **Client:** `pnpm prod:readiness -- --api-url https://<api>` (see [PROD-OBSERVABILITY.md](./PROD-OBSERVABILITY.md))

Full detail: [VENDOR-TO-CLIENT.md](./VENDOR-TO-CLIENT.md).

---

## Client profiles

| Profile | When | Values template |
|---------|------|-----------------|
| **External** | Managed Postgres, Redis, S3 | `deploy/client/values-external.example.yaml` |
| **Bundled** | In-cluster Postgres, Redis, MinIO | `deploy/client/values-bundled.example.yaml` + `bundled/values.data.yaml` |

Both merge `values-enterprise.example.yaml`. OpenShift adds `deploy/values/openshift.yaml`.

Client kit index: [deploy/client/README.md](../../deploy/client/README.md).

---

## Vendor QA (OpenShift client test)

| Lab | Guide | Command |
|-----|-------|---------|
| OpenShift client test | [OPENSHIFT.md](./OPENSHIFT.md#client-test-lab) | `pnpm openshift:client-test` |

Local daily development uses **Compose only** — see [LOCAL.md](./LOCAL.md).

---

## All guides

| Guide | Purpose |
|-------|---------|
| [LOCAL.md](./LOCAL.md) | Compose dev — API, UI, workers, inference |
| [CLIENT.md](./CLIENT.md) | Client production — Helm, Argo CD, profiles |
| [VENDOR-TO-CLIENT.md](./VENDOR-TO-CLIENT.md) | Registry push → client pull → deploy |
| [SECRETS.md](./SECRETS.md) | Vault, ESO, hardening |
| [OPENSHIFT.md](./OPENSHIFT.md) | OpenShift production + client test lab |
| [RELEASE.md](./RELEASE.md) | SBOM, cosign, promotion |
| [OBSERVABILITY.md](./OBSERVABILITY.md) | OTEL in cluster |

---

## Helm charts

| Chart | Purpose |
|-------|---------|
| `deploy/helm/repody` | API, web, Taskiq workers, Ingress |
| `deploy/helm/repody-data` | Postgres, Redis, MinIO (bundled) |
| `deploy/helm/repody-auth` | Keycloak (optional) |

**Bundled install order:** namespace + secrets → `repody-data` → optional `repody-auth` → `repody`.

## Values merge order

```
deploy/helm/repody/values.yaml
  → values-common.yaml
  → client GitOps values.yaml
  → values-enterprise.example.yaml
  → deploy/values/openshift.yaml          (OpenShift only)
```

## Image registry convention

```powershell
$env:REPODY_IMAGE_REGISTRY="ghcr.io/yourorg/repody"   # host + project path
$env:REPODY_IMAGE_TAG="1.0.0"
```

Helm values:

```yaml
images:
  api:
    repository: ghcr.io/yourorg/repody/repody-backend
    tag: "1.0.0"
```

## Principles

1. **Compose for local dev** — daily work does not require Kubernetes.
2. **Standard Ingress** — `networking.k8s.io/v1` on every cluster.
3. **Secrets outside Git** — Vault → ESO → Kubernetes Secrets.
4. **Inference outside the chart** — client VLM in Vault, not in Helm values secrets.
5. **Client kit = YAML only** — install steps live in this doc tree, not in `deploy/client/`.

## Related

| Topic | Doc |
|-------|-----|
| Managed Postgres / CNPG | [ONPREM-MANAGED-DATA.md](../ONPREM-MANAGED-DATA.md) |
| External VLM | [REPODY-VLM.md](../REPODY-VLM.md) |
| Runtime env keys | [deploy/ENV.md](../../deploy/ENV.md) |
