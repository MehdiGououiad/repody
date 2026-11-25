# Client deployment kit

Templates a client copies into a private GitOps repo. The install guide is
[docs/CLUSTER.md](../../docs/CLUSTER.md).

| File                                                | Purpose                                                                                       |
| --------------------------------------------------- | --------------------------------------------------------------------------------------------- |
| `namespace.example.yaml`                            | Namespace with restricted Pod Security labels                                                 |
| `secrets/runtime.externalsecret.example.yaml`       | `repody-runtime-secrets` from Vault (database, Hatchet token, S3, Better Auth, inference key) |
| `secrets/registry-pull.externalsecret.example.yaml` | Image pull secret                                                                             |
| `argocd.application.yaml`                           | Argo CD Application: chart from the vendor tag, values from the client repo                   |

Values: start from [`deploy/helm/repody/values-production.yaml.example`](../helm/repody/values-production.yaml.example).
Image digests for a release come from the `helm-images.yaml` artifact of the
[images-ghcr](../../.github/workflows/images-ghcr.yml) workflow.

```bash
helm upgrade --install repody deploy/helm/repody -n repody -f values.yaml --wait --timeout 15m
```
