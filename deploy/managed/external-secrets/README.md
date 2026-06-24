# Enterprise secrets

Repody production should not commit runtime secret values to Git. The Helm chart
expects one Kubernetes Secret named `repody-runtime-secrets`; External Secrets
Operator, Vault, SOPS, Sealed Secrets, or a client secret manager should create
that Secret before Argo CD syncs the app.

## Required runtime keys

`repody-runtime-secrets` must contain:

- `AUTH_SECRET`
- `AUTH_KEYCLOAK_CLIENT_SECRET`
- `AUDIT_DATABASE_URL`
- `AUDIT_REDIS_URL`
- `AUDIT_MINIO_ACCESS_KEY`
- `AUDIT_MINIO_SECRET_KEY`
- `HATCHET_CLIENT_TOKEN`
- `BUGSINK_DSN`

Add `AUDIT_VLLM_API_KEY` when the external VLM endpoint requires bearer-token
auth.

## Vault path

The example manifests assume External Secrets Operator with Vault Kubernetes
auth:

```bash
kubectl apply -f deploy/managed/external-secrets/vault-clustersecretstore.example.yaml
kubectl apply -f deploy/managed/external-secrets/repody-runtime-externalsecret.example.yaml
```

For a real client, copy these into the private GitOps repo and replace the Vault
server, auth role, mount path, and remote secret paths.

## Preflight

Validate that the production values and ExternalSecret agree before syncing
Argo CD:

```bash
pnpm enterprise:secrets -- \
  --values path/to/values-production.yaml \
  --external-secret path/to/repody-runtime-externalsecret.yaml \
  --cluster-secret-store path/to/vault-clustersecretstore.yaml
```

Use `--require-vlm-api-key` when the external VLM endpoint requires auth.

After applying the ExternalSecret, verify it reconciled without printing secret
values:

```bash
kubectl -n repody wait externalsecret/repody-runtime-secrets --for=condition=Ready --timeout=2m
kubectl -n repody get secret repody-runtime-secrets
```
