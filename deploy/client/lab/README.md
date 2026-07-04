# k3s client bundled lab

Vendor QA that treats **k3d/k3s as a real client cluster** — same path as production:

- Vault → External Secrets Operator → Kubernetes Secrets
- Bundled profile (`repody-data` + `repody-auth` + `repody`)
- Standard **Ingress** (`networking.k8s.io/v1`, Traefik on k3s)
- `values-enterprise.example.yaml` (networkPolicy, PDB, OTEL)
- Local registry (k3d) + pull secrets (no `image load` hacks)

**Guide:** [docs/deploy/K3S-CLIENT.md](../../../docs/deploy/K3S-CLIENT.md)

```powershell
winget install k3d.k3d
pnpm k3s:client
```

Teardown: `pnpm k3s:client:clean`
