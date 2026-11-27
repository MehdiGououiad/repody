# Architecture decision records

| ADR                                                | Topic                                                                       |
| -------------------------------------------------- | --------------------------------------------------------------------------- |
| [004](./004-cloud-kubernetes-packaging.md)         | Cloud / Kubernetes (Helm, microservice images)                              |
| [005](./005-kubernetes-only-external-inference.md) | Kubernetes deployment with external inference                               |
| [009](./009-simple-backend.md)                     | One workflow definition, typed rules, one queue, multipart uploads          |
| [010](./010-explicit-lifecycles.md)                | Explicit lifecycles: one owner per status, DB constraints, UI unions        |
| [011](./011-hatchet.md)                            | Hatchet runs the queue, its limits and the maintenance cron                 |
| [012](./012-hosted-demo-on-a-vps.md)               | The hosted demo runs on one VPS with Compose; client installations use Helm |
| [013](./013-modular-three-agent-platform.md)       | Core spine + three isolated modules (IDP, Fraud Shield, Operator)           |

Current backend shape: [ADR 009](./009-simple-backend.md).

Start with [CONTEXT.md](../../CONTEXT.md) and the [documentation map](../README.md).
