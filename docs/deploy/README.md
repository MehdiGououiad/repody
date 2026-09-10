# Deploy documentation

**Canonical index for every install path.** Manifests and Helm live under [`deploy/`](../../deploy/).  
Full product docs hub: [../README.md](../README.md).

---

## Supported paths

| Path | Audience | Guide | How |
|------|----------|-------|-----|
| **Mac (Apple Silicon)** | Laptop from Hub images | **[MAC.md](./MAC.md)** | `pnpm platform setup` → `pnpm platform` |
| **Local** (Win / Mac / Linux) | Daily Compose | [LOCAL.md](./LOCAL.md) | `pnpm platform` |
| **OpenShift / Kubernetes** | Client production | [OPENSHIFT.md](./OPENSHIFT.md) | Helm (+ optional Argo CD) |

OpenShift and generic Kubernetes share the same charts, values merge order, and Ingress path.

### Profiles, secrets, and release

| Guide | Purpose |
|-------|---------|
| [MAC.md](./MAC.md) | **Mac end-to-end** — prereqs, setup, sign-in, no hand-written secrets |
| [LOCAL.md](./LOCAL.md) | Shared laptop flow (all OSes) + flags / catalog |
| [OPENSHIFT.md](./OPENSHIFT.md) | Cluster start-to-finish |
| [CLIENT.md](./CLIENT.md) | Profiles (external / bundled), Ingress, Argo skeleton |
| [SECRETS.md](./SECRETS.md) | Vault, External Secrets, hardening |
| [VENDOR-TO-CLIENT.md](./VENDOR-TO-CLIENT.md) | Registry push → client pull |
| [../../deploy/registry/README.md](../../deploy/registry/README.md) | Docker Hub multi-arch, GHCR, Harbor |
| [RELEASE.md](./RELEASE.md) | SBOM, cosign, promotion |
| [OBSERVABILITY.md](./OBSERVABILITY.md) | JSON logs + OTEL (deploy notes) |
| [PROD-OBSERVABILITY.md](./PROD-OBSERVABILITY.md) | Production observability expectations |

Command cheat sheet: [../COMMANDS.md](../COMMANDS.md).

---

## Mac in one screen

```bash
brew install llama.cpp          # Metal llama-server
# Docker Desktop running; Node 24; corepack pnpm 11
# Download NuExtract GGUFs → deploy/llamacpp/paths.local.env
git clone https://github.com/MehdiGououiad/repody.git && cd repody
pnpm install && pnpm doctor
pnpm platform setup             # copies env examples + pulls Hub arm64 images
pnpm platform                   # start + host NuExtract (repody:vlm)
# UI http://localhost:3000 · operator@repody.local / repody-dev
```

Full steps and troubleshooting: **[MAC.md](./MAC.md)**.

---

## Client install (summary)

1. Namespace — `deploy/client/namespace.example.yaml` (restricted PSA)
2. Vault + External Secrets — [SECRETS.md](./SECRETS.md)
3. Private GitOps values from `deploy/client/values-*.example.yaml` + `values-enterprise.example.yaml`
4. Same Helm valueFiles on every cluster (no OpenShift-only overlay)
5. Helm: bundled → `repody-data` then `repody`; external → `repody` only
6. Verify: `curl …/v1/healthz/live` · `pnpm client:check` · `pnpm prod:readiness`

Full steps: [OPENSHIFT.md](./OPENSHIFT.md).

---

## Helm charts

| Chart | Purpose |
|-------|---------|
| `deploy/helm/repody` | API, web, workers, Ingress |
| `deploy/helm/repody-data` | Postgres, Redis, MinIO (bundled) |
| `deploy/helm/repody-auth` | Optional Keycloak |

## Values merge order

```
deploy/helm/repody/values.yaml
  → values-common.yaml
  → client GitOps values.yaml
  → values-enterprise.example.yaml
```

## Image registry

Docker Hub (portable multi-arch for Mac + Intel):

```powershell
$env:REPODY_IMAGE_REGISTRY="mehdigououiad"
$env:REPODY_IMAGE_TAG="0.1.0"
$env:REPODY_IMAGE_PLATFORMS="linux/amd64,linux/arm64"
$env:REPODY_BACKEND_EXTRAS="otel"
pnpm images:release
```

GHCR / client registry:

```powershell
$env:REPODY_IMAGE_REGISTRY="ghcr.io/yourorg/repody"
$env:REPODY_IMAGE_TAG="1.0.0"
```

```yaml
images:
  api:
    repository: ghcr.io/yourorg/repody/repody-backend
    tag: "1.0.0"   # immutable — never latest in production
```

Details: [../../deploy/registry/README.md](../../deploy/registry/README.md).

---

## Principles

1. Compose for local / Mac daily work — cluster is not required daily.
2. Standard Ingress (`networking.k8s.io/v1`) on every platform.
3. Secrets outside Git for production — Vault → ESO → Kubernetes Secrets.
4. Inference outside the app chart (host Metal on Mac; external VLM in prod).
5. Cluster platform owns NetworkPolicy and egress.
6. Client kit is YAML templates + these docs — not a lab orchestrator.
