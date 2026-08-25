# Deploy documentation

**Canonical index.** Manifests and Helm charts live under [`deploy/`](../../deploy/).

## Supported paths

| Path | Audience | Guide | How |
|------|----------|-------|-----|
| **Local** | Daily development | [LOCAL.md](./LOCAL.md) | `pnpm platform` |
| **OpenShift / Kubernetes** | Client production | [OPENSHIFT.md](./OPENSHIFT.md) | Helm (+ optional Argo CD) |

OpenShift and generic Kubernetes share the same charts, values merge order, and Ingress path.

Profiles, secrets, and vendor handoff:

| Guide | Purpose |
|-------|---------|
| [OPENSHIFT.md](./OPENSHIFT.md) | **Start here for cluster deploy** — namespace → secrets → Helm → verify |
| [CLIENT.md](./CLIENT.md) | Profiles (external / bundled), Ingress, Argo skeleton |
| [SECRETS.md](./SECRETS.md) | Vault, External Secrets, hardening |
| [VENDOR-TO-CLIENT.md](./VENDOR-TO-CLIENT.md) | Registry push → client pull (Harbor / GHCR) |
| [registry/README.md](../../deploy/registry/README.md) | Harbor, GHCR, pull secrets |
| [RELEASE.md](./RELEASE.md) | SBOM, cosign, promotion |
| [OBSERVABILITY.md](./OBSERVABILITY.md) | JSON logs + OTEL |

Command cheat sheet: [docs/COMMANDS.md](../COMMANDS.md).

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

## Principles

1. Compose for local dev — cluster is not required daily.
2. Standard Ingress (`networking.k8s.io/v1`) on every platform.
3. Secrets outside Git — Vault → ESO → Kubernetes Secrets.
4. Inference outside the app chart.
5. Cluster platform owns NetworkPolicy and egress.
6. Client kit is YAML templates + these docs — not a lab orchestrator.
