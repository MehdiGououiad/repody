# ADR 005: Kubernetes with external inference

## Status

Accepted — 2026-06-19

## Context

Repody deploys the platform on Kubernetes. Document-model inference is operated outside
the Repody release as **vLLM** or **llama-server**.

## Decision

- **Kubernetes with Helm** for production and local kind (`pnpm k8s:local`, alias `pnpm dev`).
- The Repody Helm chart does **not** deploy inference.
- `config.inferenceMode: vllm` and `config.vllmBaseUrl` point workers at the external endpoint.
- Inference credentials live in Kubernetes Secret key `AUDIT_VLLM_API_KEY`.
- Local values: `deploy/helm/repody/values-local.yaml`.

## Consequences

- Deploy validation focuses on Helm, Kubernetes secrets, ingress/gateway, worker scaling,
  cluster logging, and external VLM connectivity.
- Air-gap bundles include platform images and the Repody chart; inference is mirrored and
  operated separately by the target environment.

## References

- [DEV.md](../../DEV.md)
- [docs/REPODY-VLM.md](../REPODY-VLM.md)
- [deploy/k8s/README.md](../../deploy/k8s/README.md)
