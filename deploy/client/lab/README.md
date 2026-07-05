# Vendor QA — OpenShift client test lab

Simulates a **production client** on OpenShift using standard **kubectl + helm** (no `oc`, no k3d, no Gitea).

Installs the same stack clients use:

- **Harbor** — Docker Compose on host ([official installer](https://goharbor.io/docs/main/install-config/run-installer-script/))
- **Argo CD** — official [getting started](https://argo-cd.readthedocs.io/en/stable/getting_started/) manifests
- **OpenTelemetry** collector + **JSON structured logs**
- **Bundled** or **external** profile

## Run

```powershell
# Infra once (Harbor Compose + cluster Vault/ESO/OTEL/Argo CD)
pnpm openshift:infra

# Platform e2e: build → push → seed → sync → verify → logs
pnpm openshift:e2e

# Full run (infra + e2e)
pnpm openshift:client-test

# External profile
pnpm openshift:client-test:external

# Direct Helm instead of Argo CD
pnpm openshift:client-test:helm

# Validate production-shaped checks
pnpm openshift:client-ready -- --profile=bundled --registry=harbor
```

Full guide: [docs/deploy/OPENSHIFT.md](../../docs/deploy/OPENSHIFT.md#client-test-lab)

Teardown:

```powershell
node deploy/scripts/openshift-client-test.mjs clean
```

Lab credentials: [lab.constants.mjs](./lab.constants.mjs) (Vault seed only — not for production).
