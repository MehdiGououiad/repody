# Diagrams

Sources are Mermaid (`.mmd`) or BPMN (`.bpmn`). SVG exports under `exports/` are what [ARCHITECTURE.md](../ARCHITECTURE.md) embeds. PNG copies under `exports/png/` exist so `docs/_md_to_docx.py` can place the same figures in `ARCHITECTURE.docx`. After the SVGs change, refresh the PNGs and run `python docs/_md_to_docx.py`.

## Production architecture (start here)

| File | Audience | What it is |
|------|----------|------------|
| **[architecture-enterprise.html](./architecture-enterprise.html)** | **Top management · enterprise architects** | ArchiMate-style layers + technology logos (open in a browser) |
| [architecture.mmd](./architecture.mmd) | Engineers | Layered Mermaid flow (Users -> Edge -> API -> Redis -> Logic -> Data) |

Open the HTML file in a browser. Logos load from the Simple Icons CDN.

## Sequence (runtime interactions)

| File | Scope |
|------|--------|
| [sequence-architecture.mmd](./sequence-architecture.mmd) | One audit run across the same components |
| [sequence-upload-et-run.mmd](./sequence-upload-et-run.mmd) | Presign, enqueue, extract, rules, SSE |
| [sequence-cycle-vie-complet.mmd](./sequence-cycle-vie-complet.mmd) | Full functional lifecycle |
| [sequence-auth-oidc.mmd](./sequence-auth-oidc.mmd) | OIDC code exchange, bearer injection, RBAC |

Matching SVGs: `exports/sequence-upload-et-run.svg`, `exports/sequence-cycle-vie-complet.svg`, `exports/sequence-auth-oidc.svg`.

## Topology and backend

| File | Scope |
|------|--------|
| [architecture-openshift.mmd](./architecture-openshift.mmd) | Production cluster (Ingress, namespace, data profile, ESO) |
| [architecture-locale.mmd](./architecture-locale.mmd) | Laptop topology |
| [architecture-backend-couches.mmd](./architecture-backend-couches.mmd) | Backend modules and the IDP hot path |
| [bpmn/](./bpmn/README.md) | BPMN processes (start / deploy / run) |

Matching SVGs: `exports/architecture-openshift.svg`, `exports/architecture-locale.svg`, `exports/architecture-backend-couches.svg`.
