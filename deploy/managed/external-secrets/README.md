# External Secrets with Vault

Runtime secret values never go into Git or Helm values. External Secrets Operator reads them
from Vault and creates the `repody-runtime-secrets` Secret that the chart's `existingSecret`
names. The keys it must hold are listed in [docs/CLUSTER.md](../../../docs/CLUSTER.md#2-runtime-secret).

```bash
kubectl apply -f deploy/managed/external-secrets/vault-clustersecretstore.example.yaml
```

```bash
kubectl apply -f deploy/client/secrets/runtime.externalsecret.example.yaml
```

Copy the examples into the private GitOps repo first and replace the Vault server, auth role,
mount path and remote secret paths. Check that the Secret reconciled, without printing values:

```bash
kubectl -n repody wait externalsecret/repody-runtime-secrets --for=condition=Ready --timeout=2m
```
