# ADR 012: The hosted demo runs on one VPS with Compose; client installations use Helm

Amends the deployment parts of [ADR 004](./004-cloud-kubernetes-packaging.md) and
[ADR 005](./005-kubernetes-only-external-inference.md), which describe Kubernetes as Repody's
production.

## Context

Repody is installed on premise: each client runs its own copy. Repody's own production,
app.repody.com, is a demo for the clients it invites, who pay with credits. It needs to run cheaply
and safely, and to deploy within minutes of a merge. A Kubernetes cluster for one small demo
would cost more to run and to operate than the demo itself.

## Decision

The hosted demo runs on **one VPS with Docker Compose** ([`deploy/vps`](../../deploy/vps)):

| Concern    | Choice                                                                                                                                                                                           |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Stack      | `deploy/vps/compose.yaml`: Postgres, Hatchet Lite, SeaweedFS, Keycloak, the API, workers and web                                                                                                 |
| Ingress    | A Cloudflare Tunnel (outbound only, no open port); Cloudflare Access in front of the Keycloak admin console and staging                                                                          |
| Operations | Tailscale SSH for people and deploys (an ephemeral `tag:ci` node with workload identity, no stored key)                                                                                          |
| Model      | NuExtract3 on Modal (vLLM, scale to zero), outside the server ([deploy/modal](../../deploy/modal))                                                                                               |
| Releases   | A `master` commit is built, signed and deployed to staging; a release tag promotes those same images, by digest, to production ([deploy/vps/README.md](../../deploy/vps/README.md), "Releasing") |
| Staging    | A second, separate stack on the same server ([deploy/vps/README.md](../../deploy/vps/README.md), "Staging")                                                                                      |

The **Helm chart stays the way clients install Repody** on their own Kubernetes or OpenShift
([CLUSTER.md](../CLUSTER.md)). It is a reference that CI lints and validates but does not
install, so it is installed on a local cluster before a client installation.

## Consequences

- One server is a single point of failure: off-site backups and uptime alerts are needed (and
  tracked) before more clients rely on the demo.
- Two deployment lanes share the images and the settings ([deploy/ENV.md](../../deploy/ENV.md)),
  so a new setting must reach both `deploy/vps/compose.yaml` and the chart's values.
- Staging on the same server shares its memory, disk and Docker engine with production: deploys
  refuse a compose file that reaches outside its stack, and staging can move to its own server
  by changing one variable.
