# Deploy assets

The hosted demo's stack, the Helm chart for client installations, and scripts. **Documentation:** [docs/LOCAL.md](../docs/LOCAL.md) (laptop) · [vps/README.md](./vps/README.md) (the hosted demo and its staging) · [docs/CLUSTER.md](../docs/CLUSTER.md) (client clusters).

## Quick links

| Goal                         | Guide                                                | Command                      |
| ---------------------------- | ---------------------------------------------------- | ---------------------------- |
| Local laptop                 | [LOCAL.md](../docs/LOCAL.md)                         | `pnpm platform`              |
| Release the hosted demo      | [vps/README.md](./vps/README.md#releasing)           | merge, then `git tag v1.2.3` |
| Push images / vendor handoff | [CLUSTER.md](../docs/CLUSTER.md#images-and-releases) | `pnpm images:release`        |
| OpenShift / client install   | [CLUSTER.md](../docs/CLUSTER.md)                     | Helm / Argo CD               |

## Layout

| Path          | Purpose                                                                                                     |
| ------------- | ----------------------------------------------------------------------------------------------------------- |
| `vps/`        | The hosted demo and its staging: Compose stack, deploy tools, smoke test - [vps/README.md](./vps/README.md) |
| `modal/`      | NuExtract3 on Modal (vLLM), the demo's model - [modal/README.md](./modal/README.md)                         |
| `helm/repody` | The chart for client clusters: API, web, Hatchet workers, migrations Job, Ingress                           |
| `keycloak/`   | Keycloak realm (Compose import; import it into the client's Keycloak)                                       |
| `client/`     | Values templates, ExternalSecrets - [client/README.md](./client/README.md)                                  |
| `managed/`    | CNPG, External Secrets examples                                                                             |
| `registry/`   | GHCR and on-prem registry notes                                                                             |
| `scripts/`    | Image build, release, readiness checks                                                                      |

## Image registry convention

```powershell
$env:REPODY_IMAGE_REGISTRY="ghcr.io/yourorg/repody"   # host + project path
$env:REPODY_IMAGE_TAG="1.0.0"
pnpm images:release
```

Helm `images.*.repository` = `{registry}/repody-backend` (not `{registry}/repody/repody-backend` when registry already includes the project).

Production tags must be **immutable** - never `latest`.
