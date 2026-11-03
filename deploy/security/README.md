# Security scanning

[Trivy](https://trivy.dev/) is the one scanner, in CI ([`.github/workflows/security.yml`](../../.github/workflows/security.yml)) and locally.

| Scan | Covers | CI gate |
|------|--------|---------|
| Repository (`trivy fs`) | `pnpm-lock.yaml`, `backend/uv.lock`, secrets, Dockerfiles / Compose / Helm misconfig | CRITICAL or HIGH fails |
| Images (`trivy image`) | OS and language packages in `repody-backend` and `repody-web` | CRITICAL or HIGH fails |

Results are uploaded to GitHub code scanning (SARIF). Unfixed vulnerabilities are ignored
(`deploy/security/trivy.yaml`); secret rules live in `trivy-secret.yaml`.

Released images also carry BuildKit SBOM and provenance attestations and a cosign keyless
signature ([`.github/workflows/images-ghcr.yml`](../../.github/workflows/images-ghcr.yml));
[`release-promote.yml`](../../.github/workflows/release-promote.yml) verifies the signatures.

## Run locally

```bash
trivy fs --config deploy/security/trivy.yaml --scanners vuln,secret,misconfig .
```

```bash
docker buildx bake -f docker-bake.hcl --load && trivy image --config deploy/security/trivy.yaml repody-backend:dev
```
