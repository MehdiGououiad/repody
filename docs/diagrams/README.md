# Diagrammes Repody (éditables)

Fichiers **Mermaid** (texte) — modifiables dans Cursor / VS Code, versionnés dans Git.

## Contenu

| Fichier | Type | Périmètre |
|---------|------|-----------|
| [architecture-locale.mmd](./architecture-locale.mmd) | Architecture | Stack **Compose** (dev quotidien) |
| [architecture-openshift.mmd](./architecture-openshift.mmd) | Architecture | **OpenShift / prod** (Helm, modules, inférence externe) |
| [architecture-backend-couches.mmd](./architecture-backend-couches.mmd) | Architecture | Couches backend + contextes bornés |
| [sequence-cycle-vie-complet.mmd](./sequence-cycle-vie-complet.mmd) | Séquence | **Cycle enrichi** : auth, IAM, catalogue, workflow, dry-run, upload présigné/multipart, run UI + API key, Taskiq/outbox, extraction (+ markdown), règles, SSE/poll, erreurs, stale, operator, health, OTEL |
| [sequence-auth-oidc.mmd](./sequence-auth-oidc.mmd) | Séquence | Authentification OIDC Keycloak (détail) |
| [sequence-upload-et-run.mmd](./sequence-upload-et-run.mmd) | Séquence | Upload MinIO → enqueue Taskiq → extraction → règles → SSE |

Référence narrative : [CONTEXT.md](../../CONTEXT.md) · [PLATFORM.md](../PLATFORM.md) · [deploy/](../deploy/).

## Prévisualiser

> **Cursor / aperçu natif** : l’aperçu intégré n’accepte souvent que `flowchart` / `graph`.
> Les fichiers `sequence-*.mmd` (`sequenceDiagram`) déclenchent alors
> *« invalid mermaid header … expected graph td flowchart »* — ce n’est **pas** une erreur de syntaxe Mermaid.
> Utiliser l’une des options ci-dessous pour les séquences.

1. Ouvrir l’export SVG déjà généré : [exports/](./exports/) (ex. [sequence-cycle-vie-complet.svg](./exports/sequence-cycle-vie-complet.svg))
2. Coller le contenu sur [mermaid.live](https://mermaid.live)
3. Extension VS Code / Cursor **Mermaid** (support `sequenceDiagram`), ou Markdown :

````markdown
```mermaid
…contenu du fichier .mmd…
```
````

## Exporter (optionnel)

```powershell
# Exemple avec @mermaid-js/mermaid-cli (si installé)
npx -y @mermaid-js/mermaid-cli -i docs/diagrams/architecture-locale.mmd -o docs/diagrams/exports/architecture-locale.svg
```

Les exports SVG/PNG ne sont **pas** la source de vérité — éditer toujours les `.mmd`.
