# Security scanning

Repody uses a **dual-scanner** supply-chain model:

| Tool | Role | Strength |
|------|------|----------|
| **Trivy** (Aqua) | Primary CI gate | Broadest coverage: OS + language deps, Dockerfiles, Compose/Helm misconfig, secrets, licenses |
| **Grype** (Anchore) | SBOM validation | Matches vulnerabilities against **Syft** SPDX SBOMs (same stack as `pnpm release:attest`) |
| **pnpm audit** | Frontend lockfile | npm advisory database |
| **pip-audit** | Backend lockfile | PyPI/OSV advisories |

## Which is more complete?

**Trivy is the more complete standalone scanner** for day-to-day CI: one engine covers filesystem, IaC, secrets, and container images.

**Grype is the better SBOM-native validator** when you already generate SPDX with Syft at release time. It catches a different slice of the vulnerability graph and is the industry pairing with Syft + cosign attestations.

We run **both** on release images and fail on the **union of CRITICAL + HIGH** (unfixed only), with a merged report in `dist/security/`.

## Commands

```powershell
pnpm security:scan          # local full scan (Docker required for image phase)
pnpm security:scan:quick    # deps + filesystem only (no image build)
```

CI: [`.github/workflows/security.yml`](../../.github/workflows/security.yml)

## Pinned scanner versions

Pinned scanner versions: Trivy `0.72.0`, Grype `v0.110.0`, Syft `v1.40.0` (see `deploy/scripts/security-scan.mjs`).
