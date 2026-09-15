# E2E sample documents

Place test files here. Platform tests: [docs/DEVELOPMENT.md](../../../docs/DEVELOPMENT.md#testing) · commands: [docs/COMMANDS.md](../../../docs/COMMANDS.md).

## Hard OCR / extraction fixtures

| File | Use |
|------|-----|
| `hopital-devis-agadir.png` | Hôpital Privé Agadir medical quote — ICE stamp `001639657000061`, table sub-totals |
| `E8cbebbXMAIU1Mj.jpg` | Same devis scan (JPEG alias) |
| `hopital-devis-agadir.ocr-expectations.json` | Ground truth for OCR markdown scoring (ICE + hard fields) |
| `hopital-devis-agadir.benchmark.json` | Structured extraction benchmark manifest |

## Prerequisites

**Compose (default):** `pnpm platform`, then `pnpm test:platform` (use `E2E_WEB_URL=http://localhost:3000`).

**Deployed cluster:** [docs/CLUSTER.md](../../../docs/CLUSTER.md), then `pnpm test:platform` with Ingress URLs (see [DEVELOPMENT.md](../../../docs/DEVELOPMENT.md#testing)).
