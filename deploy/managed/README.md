# Managed on-prem data plane

These manifests are for production-style on-prem services that Repody consumes as
external dependencies.

## CloudNativePG

`cloudnativepg/` contains:

- `Cluster` with 3 Postgres instances
- PgBouncer `Pooler`
- `ScheduledBackup`
- NetworkPolicies
- example bootstrap Secrets

Render:

```bash
kubectl kustomize deploy/managed/cloudnativepg
```

Apply after installing the CloudNativePG operator and replacing placeholders:

```bash
kubectl apply -k deploy/managed/cloudnativepg
```

## External Secrets

`external-secrets/` contains examples for Vault-backed External Secrets:

- `vault-clustersecretstore.example.yaml`
- `repody-cnpg-externalsecrets.example.yaml`
- `repody-runtime-externalsecret.example.yaml`

Adapt Vault paths, auth roles, and secret names before applying. The Repody app
chart consumes the generated `repody-runtime-secrets` Secret and production Helm
guardrails fail if runtime credentials are put inline in values.

Validate the contract before Argo CD syncs production:

```bash
pnpm enterprise:secrets -- \
  --values path/to/values-production.yaml \
  --external-secret path/to/repody-runtime-externalsecret.yaml \
  --cluster-secret-store path/to/vault-clustersecretstore.yaml
```

## Repody app chart

Use:

```bash
helm upgrade --install repody deploy/helm/repody \
  -n repody --create-namespace \
  -f deploy/helm/repody/values-production.yaml.example \
  -f deploy/helm/repody/values-production.onprem-managed.yaml.example \
  -f deploy/values/openshift.yaml \
  -f my-values.yaml
```
