# Argo CD deployment

GitOps entrypoints for Repody, following [Argo CD installation](https://argo-cd.readthedocs.io/en/stable/operator-manual/installation/), [cluster bootstrapping](https://argo-cd.readthedocs.io/en/stable/operator-manual/cluster-bootstrapping/), and [CI automation](https://argo-cd.readthedocs.io/en/stable/user-guide/ci_automation/).

Inference is external to the Repody chart — set `config.vllmBaseUrl` in values.

## Layout

| Path | Purpose |
|------|---------|
| `kustomize/local/` | Declarative Argo CD install for kind (pinned `v3.4.4` + Gateway/RBAC patches) |
| `bootstrap/gateway-addons.yaml` | Argo CD Gateway route + Envoy policies (synced by root app) |
| `repody-local-root.application.yaml` | Root Application (apply once after Argo CD install) |
| `repody-local-apps.yaml` | Four local plane apps (data → queue/auth → app) |
| `repody-project.yaml` | AppProject whitelist (includes Pod + ReplicaSet for logs/tree) |

## Local GitOps (`repody-local-*`)

`pnpm k8s:local` (non-`--minimal`):

1. Installs Argo CD: `kubectl apply -k deploy/argocd/kustomize/local`
2. Registers bootstrap: `kubectl apply -f deploy/argocd/repody-local-root.application.yaml`
3. Helm bootstraps workloads once, then **handoff** deletes Helm release secrets so Argo CD is the sole deployer
4. Child apps reconcile from Git with automated sync/self-heal

Image tags for the app plane: `deploy/helm/repody/values-local-images.yaml`

```powershell
pnpm gitops:publish -- --all
```

Verify pod logs through the Gateway:

```powershell
node deploy/scripts/verify-argocd-logs.mjs
```

### Security (local)

- Argo CD RBAC: `policy.default: role:readonly`; only the `admin` account has `role:admin`
- `role:repody-operator` can sync/view logs for `repody/*` apps (assign via SSO later)
- Repository credentials are **not** in Git — bootstrap reads `git credential` locally

## Staging / production

Immutable image promotion via Git (not in-cluster image build):

| Environment | Image values file | CI workflow |
|-------------|-------------------|-------------|
| Staging | `values-staging-images.yaml` | `.github/workflows/gitops-promote-staging.yml` |
| Local | `values-local-images.yaml` | `pnpm gitops:publish` |

```powershell
pnpm images:build
pnpm images:push
node deploy/scripts/gitops-promote-staging.mjs --commit
git push
kubectl apply -n argocd -f deploy/argocd/repody-staging.application.yaml
```

## Runtime secrets

Keep secrets out of Git. Use `secrets.existingSecret=repody-runtime-secrets` and populate via External Secrets / bootstrap.

Required keys: `AUTH_SECRET`, `AUTH_KEYCLOAK_CLIENT_SECRET`, `AUDIT_DATABASE_URL`, `AUDIT_REDIS_URL`, `AUDIT_MINIO_ACCESS_KEY`, `AUDIT_MINIO_SECRET_KEY`, `HATCHET_CLIENT_TOKEN`.

## References

- [App-of-apps pattern](https://argo-cd.readthedocs.io/en/stable/operator-manual/cluster-bootstrapping/#app-of-apps-pattern-alternative)
- [RBAC](https://argo-cd.readthedocs.io/en/stable/operator-manual/rbac/)
- [Helm + Argo CD](https://argo-cd.readthedocs.io/en/stable/user-guide/helm/)
