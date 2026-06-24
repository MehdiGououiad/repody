# Deploy layout

| Path | Role |
|------|------|
| [`helm/repody/`](./helm/repody/) | Kubernetes chart (production + local kind values) |
| [`scripts/`](./scripts/) | image build, Helm validation, `k8s-local` bootstrap |
| [`k8s/`](./k8s/) | kind cluster config, Gateway addons |
| [`airgap/`](./airgap/) | regulated-release manifest |
| [`ENV.md`](./ENV.md) | secrets and `AUDIT_*` variables |

## Production

```bash
pnpm images:build
pnpm images:push
pnpm helm:deps
helm upgrade --install repody deploy/helm/repody -n repody --create-namespace -f my-values.yaml
```

Production inference is external to this repo's Helm chart. Set:

```yaml
config:
  inferenceMode: vllm
  vllmBaseUrl: https://your-vlm-host/v1
  vllmServedModel: your-model
```

## Local development

```bash
pnpm k8s:local:hosts   # once (admin)
pnpm k8s:local         # or: pnpm dev
```

See [../DEPLOY.md](../DEPLOY.md), [../docs/CLOUD-K8S.md](../docs/CLOUD-K8S.md), and
[../DEV.md](../DEV.md).
