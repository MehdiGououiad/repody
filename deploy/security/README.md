# Security scanning

[Trivy](https://trivy.dev/) is the one scanner, in CI ([`.github/workflows/security.yml`](../../.github/workflows/security.yml)) and locally.

| Scan                    | Covers                                                                                          | CI gate                |
| ----------------------- | ----------------------------------------------------------------------------------------------- | ---------------------- |
| Repository (`trivy fs`) | `bun.lock`, `site/bun.lock`, `backend/uv.lock`, secrets, Dockerfiles / Compose / Helm misconfig | CRITICAL or HIGH fails |
| Images (`trivy image`)  | OS and language packages in `repody-backend`, `repody-web` and `repody-keycloak`                | CRITICAL or HIGH fails |

Both run on every pull request and master push, and weekly on master, so a vulnerability
published after the last merge is found too. The SARIF results go to GitHub code scanning when
the repository variable `CODE_SCANNING` is `true` (it needs code scanning on the repository).

- Vulnerabilities without a fix are ignored (`trivy.yaml`).
- An accepted finding goes in [`trivyignore.yaml`](trivyignore.yaml), with its reason and an
  expiry date; past that date it fails the scan again.
- Secret rules live in `trivy-secret.yaml`.

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
