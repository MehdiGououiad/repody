# ADR 005: Kubernetes with external inference

## Status

Accepted — 2026-06-19

## Context

Repody deploys the platform on Kubernetes. Document-model inference is operated outside
the Repody release as **vLLM** or **llama-server**.

## Decision

- **Kubernetes with Helm** for production (client OpenShift or generic K8s). Daily dev: Docker Compose (`pnpm dev`). Vendor cluster smoke: OpenShift CRC ([docs/deploy/OPENSHIFT.md](../deploy/OPENSHIFT.md)).
- The Repody Helm chart does **not** deploy inference.
- `config.inferenceMode: llamacpp` and `config.llamacppBaseUrl` point workers at the external endpoint.
- Inference credentials live in Kubernetes Secret key `AUDIT_LLAMACPP_API_KEY`.

## Consequences

- Deploy validation focuses on Helm, Kubernetes secrets, routes/ingress, worker scaling,
  cluster logging, and external VLM connectivity.
- Air-gap bundles include platform images and the Repody chart; inference is mirrored and
  operated separately by the target environment.

## References

- [DEV.md](../../DEV.md)
- [docs/REPODY-VLM.md](../REPODY-VLM.md)
- [docs/deploy/CLIENT.md](../deploy/CLIENT.md)
