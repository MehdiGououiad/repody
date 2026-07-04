# Enterprise GitOps lab (k3d)

End-to-end **vendor → Harbor → private Git (Gitea) → Argo CD → cluster** using upstream components and official workflows.

References:

- [Harbor — push/pull images](https://goharbor.io/docs/main/working-with-projects/working-with-images/pulling-pushing-images/)
- [k3d — local registry](https://k3d.io/stable/usage/registries/)
- [Gitea Helm chart](https://dl.gitea.com/charts/)
- [Argo CD — private repositories](https://argo-cd.readthedocs.io/en/stable/user-guide/private-repositories/)
- [Distribution registry — native basic auth (bcrypt htpasswd)](https://distribution.github.io/distribution/about/deploying/#native-basic-auth)

## What this lab proves

| Production step | Lab implementation |
|-----------------|-------------------|
| Vendor CI builds images | `build-images.mjs` → k3d registry (`localhost:5050`) |
| Push to Harbor | In-cluster **skopeo** copy → `harbor-registry.harbor.svc` |
| Private GitOps repo | Gitea (`repody-vendor` + `repody-client`) |
| Argo CD deploy | Multi-source Applications, sync waves 0→1→2 |
| Secrets | Vault → ESO → pull secret + runtime secrets |

On production clusters, vendors push directly with `docker login` + `docker push` per [Harbor docs](https://goharbor.io/docs/main/working-with-projects/working-with-images/pulling-pushing-images/). The lab uses skopeo inside the cluster because Docker Desktop on Windows cannot reach `kubectl port-forward` on the host loopback.

Kubelet pulls images on the **node**, not via cluster DNS. The lab registry is reachable at `127.0.0.1:30500` (Harbor NodePort) with an HTTP mirror in [k3s `registries.yaml`](https://docs.k3s.io/installation/private-registry). Production clients use their Harbor hostname the same way.

## Prerequisites

- k3d, Docker, helm, kubectl, git (Docker runs `httpd:2 htpasswd -Bbn` for the lab registry)
- ~16 GiB RAM

```powershell
winget install k3d.k3d
pnpm doctor
```

## Full lab

```powershell
pnpm enterprise:lab
```

## URLs

| Service | Access |
|---------|--------|
| Harbor (kubelet pull) | `127.0.0.1:30500/repody/*` — NodePort; production uses external Harbor DNS |
| Gitea | `http://127.0.0.1:30300` — `gitops` / `GitOps12345` |
| Argo CD UI | `kubectl port-forward svc/argocd-server -n argocd 8080:443` |
| Repody API | `https://api.repody.test:8443/v1/healthz/live` |

Hosts file: `127.0.0.1 app.repody.test api.repody.test auth.repody.test files.repody.test`

## Production mapping

| Lab | Production client |
|-----|-------------------|
| Gitea | GitHub / GitLab private GitOps repo |
| Harbor in-cluster | Harbor / GHCR with `docker push` from CI |
| Argo CD | Client Argo CD / OpenShift GitOps |
| Vault dev | Client Vault / cloud SM |

See [CLIENT.md](./CLIENT.md) and [RELEASE.md](./RELEASE.md).
