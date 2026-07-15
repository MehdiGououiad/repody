# On-prem managed data plane

Repody production should treat stateful systems as a separate data plane. The Repody
Helm chart consumes connection strings and credentials from Kubernetes Secrets; it
does not own database, Redis, or object-storage lifecycle.

## Recommended shape

```text
repody namespace
  repody-api / repody-web / repody-worker-* deployments
  repody-runtime-secrets

repody-data namespace
  CloudNativePG Cluster: repody-postgres
  CloudNativePG Pooler: repody-postgres-pooler
  ScheduledBackup: repody-postgres-daily

external or platform services
  Redis or Valkey (Taskiq broker)
  S3-compatible object storage
  Vault / External Secrets Operator / SOPS
  external VLM endpoint
```

## Postgres: CloudNativePG

Install the CloudNativePG operator with the method you standardize on:

```bash
helm repo add cnpg https://cloudnative-pg.github.io/charts
helm repo update
helm upgrade --install cnpg cnpg/cloudnative-pg \
  --namespace cnpg-system \
  --create-namespace
```

Then apply the Repody data-plane manifests:

```bash
kubectl apply -f deploy/managed/cloudnativepg/secrets.example.yaml
kubectl apply -k deploy/managed/cloudnativepg
```

For production, replace `secrets.example.yaml` with External Secrets, Vault, SOPS, or
Sealed Secrets. The example is intentionally a bootstrap template, not something to
commit with real values.

If you use External Secrets Operator and Vault:

```bash
kubectl apply -f deploy/managed/external-secrets/vault-clustersecretstore.example.yaml
kubectl apply -f deploy/managed/external-secrets/repody-cnpg-externalsecrets.example.yaml
kubectl apply -f deploy/managed/external-secrets/repody-runtime-externalsecret.example.yaml
```

Those files contain placeholder Vault paths and must be adapted to your Vault mount,
auth role, and secret layout.

Before applying, edit:

- `storage.storageClass`
- `walStorage.storageClass`
- backup `destinationPath`
- backup `endpointURL`
- backup credentials
- CPU/memory/storage sizes for your workload

The default anti-affinity is `preferred` so a small on-prem cluster can still
schedule. For a three-node production cluster, change `podAntiAffinityType` to
`required` after confirming each Postgres instance can land on a different node.

## Runtime Secret

Repody expects this Secret in the `repody` namespace:

```text
repody-runtime-secrets
  AUTH_SECRET
  AUTH_KEYCLOAK_CLIENT_SECRET
  AUDIT_DATABASE_URL
  AUDIT_REDIS_URL
  AUDIT_MINIO_ACCESS_KEY
  AUDIT_MINIO_SECRET_KEY
  AUDIT_LLAMACPP_API_KEY
  BUGSINK_DSN
```

For CloudNativePG through PgBouncer, `AUDIT_DATABASE_URL` should target the pooler:

```text
postgresql+asyncpg://audit:<password>@repody-postgres-pooler-rw.repody-data.svc.cluster.local:5432/audit_workbench
```

Use the examples in `deploy/managed/external-secrets/` when Vault and External
Secrets Operator are available.

## Redis / Valkey (Taskiq)

Taskiq uses Redis Streams for background jobs. The API and workers must share the same `AUDIT_REDIS_URL`. Run Redis or Valkey as a platform service, not inside the Repody chart. Good options:

- an existing on-prem Redis/Valkey service,
- a dedicated Redis/Valkey operator managed by your platform team,
- a hardened VM service when Kubernetes storage/networking is not ready for Redis.

Repody only needs:

```text
AUDIT_REDIS_URL=rediss://...
```

Use TLS/auth in production and point `externalRedis.existingSecret` at
`repody-runtime-secrets`.

If you run Redis/Valkey on-prem, treat it like Postgres: separate release lifecycle,
backups/snapshots if persistence matters, metrics, alerts, TLS, and credentials from
Vault/External Secrets.

## Object storage

Run S3-compatible storage outside the Repody chart. On-prem choices include:

- an existing enterprise S3 service,
- MinIO Operator / tenant managed by the platform team,
- storage appliance S3 endpoints.

Repody only needs endpoint, bucket, access key, secret key, and public file endpoint.
For on-prem MinIO, prefer MinIO Operator/Tenant managed by the platform team instead
of the single MinIO pod bundled in the Repody app chart.

## Install Repody against managed data

```bash
helm upgrade --install repody deploy/helm/repody \
  -n repody --create-namespace \
  -f deploy/helm/repody/values-production.yaml.example \
  -f deploy/helm/repody/values-production.onprem-managed.yaml.example \
  -f deploy/values/openshift.yaml \
  -f my-values.yaml
```

`my-values.yaml` should contain only environment-specific non-secret settings such as
hostnames, image tags, storage endpoints, and VLM base URL.

## Release checklist

- [ ] CNPG cluster has 3 ready instances.
- [ ] PgBouncer pooler has 2 ready instances.
- [ ] A backup completed successfully.
- [ ] Restore was tested into a throwaway namespace.
- [ ] `repody-runtime-secrets` is created by Vault/External Secrets/SOPS.
- [ ] Repody migration Job completes before API rollout.
- [ ] Repody API readiness `/v1/healthz` is green.
- [ ] Redis/Valkey uses TLS/auth.
- [ ] Object storage bucket has lifecycle/retention policy.
- [ ] External Redis/Valkey is backed up, monitored, and reachable from API/workers.
- [ ] NetworkPolicies are enabled in both `repody` and `repody-data`.
