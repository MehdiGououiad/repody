# Argo CD (optional local GitOps)

Argo CD is **not part of the Repody runtime**. It is an optional operator tool used locally to sync Repody Helm charts from Git. Production clients may use their own Argo CD, Flux, or CI deploy pipeline.

Repody workloads are exposed via Envoy Gateway (`app.repody.local`, etc.). **Argo CD is not routed through that Gateway** — use port-forward instead.

## Install (standalone)

```powershell
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
pnpm argocd:port-forward
# https://127.0.0.1:8080  (admin / kubectl -n argocd get secret argocd-initial-admin-secret ...)
```

`pnpm k8s:local` (non-`--minimal`) runs the same upstream install automatically.

## Repody GitOps (optional)

After Argo CD is running:

```powershell
kubectl apply -f deploy/argocd/repody-local-root.application.yaml
```

That registers `repody-local-root`, which syncs:

- `repody-project.yaml` — AppProject (includes Pod/ReplicaSet for logs)
- `repody-local-apps.yaml` — data / queue / auth / app planes

Image tags: `deploy/helm/repody/values-local-images.yaml` → `pnpm gitops:publish -- --all`

Verify logs: `node deploy/scripts/verify-argocd-logs.mjs`

## Fast dev without Argo

```powershell
pnpm dev
```

Helm-only bootstrap — no Argo CD required.

## Staging CI promotion

`values-staging-images.yaml` + `.github/workflows/gitops-promote-staging.yml` — see `repody-staging.application.yaml`.
