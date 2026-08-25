# E2E sample documents

Place test files here. See [docs/E2E.md](../../../docs/E2E.md).

## Hard OCR / extraction fixtures

| File | Use |
|------|-----|
| `hopital-devis-agadir.png` | Hôpital Privé Agadir medical quote — ICE stamp `001639657000061`, table sub-totals |
| `E8cbebbXMAIU1Mj.jpg` | Same devis scan (JPEG alias) |
| `hopital-devis-agadir.ocr-expectations.json` | Ground truth for OCR markdown scoring (ICE + hard fields) |
| `hopital-devis-agadir.benchmark.json` | Structured extraction benchmark manifest |

## Prerequisites

**Compose (default):** `pnpm dev:all`, then `pnpm test:platform`.

**Deployed cluster:** [docs/deploy/OPENSHIFT.md](../../../docs/deploy/OPENSHIFT.md), then `pnpm test:platform` with Ingress URLs from [E2E.md](../../../docs/E2E.md).
