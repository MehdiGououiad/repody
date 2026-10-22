# E2E sample documents

Place test files here. Platform tests: [docs/DEVELOPMENT.md](../../../docs/DEVELOPMENT.md#testing) · commands: [docs/COMMANDS.md](../../../docs/COMMANDS.md).

## Fixtures

All files here are public samples or synthetic documents. Never commit real personal
documents (ID cards, bank statements, payslips, medical records); keep them under the
gitignored `private/` folder at the repo root.

| File | Use |
|------|-----|
| `Facture.pdf` · `Facture.benchmark.json` | Invoice used by API, e2e and benchmark suites |
| `bank-statement.pdf` | Fictional two-page bank statement (40 movements); regenerate with `backend/scripts/generate_bank_statement_fixture.py` |
| `commercial-invoice.png` · `10986_tutorial_invoice_logo_left.png` | Printed invoice samples |
| `Facture RETOUCHE remplie AVEC TVA.png` · `facturehandwritten.png` · `handwritten.jpg` | Handwritten invoices and receipts |
| `fiche.webp` · `../bulletin-pdf.png` | Payslip templates (demo data) |
| `Carte_identité_électronique_marocaine_(2020,_recto).png` | Public specimen of the Moroccan e-ID card |

## Prerequisites

**Compose (default):** `pnpm platform`, then `pnpm test:platform` (use `E2E_WEB_URL=http://localhost:3000`).

**Deployed cluster:** [docs/CLUSTER.md](../../../docs/CLUSTER.md), then `pnpm test:platform` with Ingress URLs (see [DEVELOPMENT.md](../../../docs/DEVELOPMENT.md#testing)).
