# Architecture decision records

| ADR | Topic |
|-----|--------|
| [001](./001-taskiq-async-runs.md) | Taskiq for async audit runs |
| [002](./002-repody-vlm-dual-inference-runtimes.md) | Repody VLM + external inference |
| [003](./003-modular-platform-modules.md) | Modular platform modules |
| [004](./004-cloud-kubernetes-packaging.md) | Cloud / Kubernetes (Helm, microservice images) |
| [005](./005-kubernetes-only-external-inference.md) | Kubernetes deployment with external inference |
| [006](./006-three-agent-functional-idp.md) | IDP agent slice (superseded by 008) |
| [007](./007-staged-agent-queues-taskiq.md) | Staged agent queues on Taskiq (superseded by 008) |
| [008](./008-flat-run-pipeline.md) | Flat run pipeline: state UPDATEs, one worker module, `dispatched_at`, exceptions |

Run pipeline: [ADR 008](./008-flat-run-pipeline.md).

Start with [CONTEXT.md](../../CONTEXT.md) and the [documentation map](../README.md).
