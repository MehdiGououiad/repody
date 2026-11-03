# Managed on-prem services

Examples for services Repody consumes as external dependencies when the client has no
managed equivalent. Install guide: [docs/CLUSTER.md](../../docs/CLUSTER.md).

## CloudNativePG (`cloudnativepg/`)

A 3-instance Postgres `Cluster`, a PgBouncer `Pooler`, a `ScheduledBackup`, NetworkPolicies
and example bootstrap Secrets. Install the [CloudNativePG operator](https://cloudnative-pg.io/documentation/current/installation_upgrade/),
replace the placeholders, then:

```bash
kubectl apply -k deploy/managed/cloudnativepg
```

Point `AUDIT_DATABASE_URL` in `repody-runtime-secrets` at the Pooler Service.

## External Secrets (`external-secrets/`)

`vault-clustersecretstore.example.yaml` connects External Secrets Operator to Vault;
`repody-cnpg-externalsecrets.example.yaml` provides the CloudNativePG credentials. The app's
runtime Secret is [`deploy/client/secrets/runtime.externalsecret.example.yaml`](../client/secrets/runtime.externalsecret.example.yaml).
See [external-secrets/README.md](./external-secrets/README.md).
