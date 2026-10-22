# OpenShift client notes

**Full guide:** [docs/CLUSTER.md](../../../docs/CLUSTER.md)

- **Taskiq + Redis:** workers and API need `AUDIT_REDIS_URL` in `repody-runtime-secrets` (bundled or external Redis).
- **Pod Security:** namespace uses **restricted** PSA - see `namespace.example.yaml`.
- **No custom SCC** required for Taskiq workers (standard Deployments).
