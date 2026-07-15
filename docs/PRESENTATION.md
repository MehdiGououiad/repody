# Prompt — Présentation fonctionnelle Repody

Prompt prêt à copier-coller (slides, script oral, ou autre LLM).  
Public cible : décideurs techniques, équipes métier, architectes.  
Durée : 15–20 min (variante 5 min en bas de page).

---

## Prompt

```
Tu es un expert produit / architecte IA. Rédige une présentation fonctionnelle de la plateforme **Repody** (plateforme d'agents : factures, contrats, workflows configurables, extraction structurée, règles métier, revue dans une UI).

**Public :** décideurs techniques, équipes métier, architectes.
**Ton :** clair, concret, orienté valeur métier — pas de jargon gratuit.
**Durée cible :** 15–20 minutes (ou version 8 min si demandé).
**Langue :** français.

---

### PARTIE 1 — Le problème : l’IA générique est gourmande et difficile à industrialiser (3–4 min)

Commence par expliquer pourquoi “mettre de l’IA partout” est plus difficile qu’on ne le croit :

1. **Coût matériel et RAM**
   Les grands LLM/VLM (7B, 13B, 70B+) consomment énormément de GPU/VRAM.
   En production, ça se traduit par : latence élevée, coût cloud, files d’attente, scaling compliqué.

2. **Modèles trop larges pour un cas d’usage précis**
   Un modèle généraliste sait “tout un peu” mais n’est pas optimisé pour **extraire des champs JSON fiables** depuis des PDF scannés ou des factures.
   Appliquer l’IA générique à l’audit documentaire = beaucoup de bruit, peu de précision, coût disproportionné.

3. **Le piège du pipeline OCR classique augmenté**
   Décris l’approche traditionnelle en 3 étapes :
   - **OCR classique** ou OCR cloud → texte brut souvent bruyant (tableaux, colonnes, en-têtes mal alignés)
   - **PDF → Markdown** (reconstruction de structure)
   - **LLM texte** → conversion Markdown → JSON selon un schéma

   Problèmes :
   - **3 passes** = 3 points de failure, latence cumulée, coût cumulé
   - Perte d’information visuelle (mise en page, cases à cocher, tableaux)
   - Le LLM texte doit “deviner” ce que l’OCR a mal lu
   - Difficile à mettre en cache de façon fiable (chaque étape dépend de la précédente)

4. **Message clé de transition**
   > Pour industrialiser l’audit documentaire, il faut un modèle **petit, spécialisé, quantifié**, et une plateforme qui **orchestre** extraction + règles + file d’attente + sécurité — pas un gros LLM générique branché sur un OCR.

---

### PARTIE 2 — La réponse technique : petits modèles spécialisés + extraction directe (4–5 min)

Présente la philosophie Repody :

1. **Modèles compacts, fine-tunés pour l’extraction documentaire**
   - Modèle par défaut : **NuExtract3** (famille numind), servi en **GGUF quantifié Q4_K_M** (~4B, vision + extraction structurée)
   - Identifiant catalogue : `repody:vlm`
   - Runtime externe : **llama-server** (API OpenAI-compatible `/v1/chat/completions`)
   - **L’inférence n’est pas embarquée dans le chart applicatif** — le client garde le contrôle GPU/on-prem

2. **Single-pass : image/PDF → JSON direct**
   Contrairement au pipeline OCR→Markdown→LLM :
   - Le PDF est rasterisé en PNG @ **170 DPI** (contrat officiel NuExtract)
   - Jusqu’à **6 pages** par requête
   - **Un seul appel VLM** produit le JSON structuré selon le schéma du workflow
   - Types NuExtract supportés : number, date, verbatim-string, listes, enums, IBAN, currency, etc.
   - Mode markdown optionnel uniquement quand il n’y a pas de champs schéma (pas le chemin principal)

3. **Pourquoi NuExtract3 vs approches type Mistral OCR / gros VLM**
   (Formuler prudemment si pas de chiffres sous la main :)
   - NuExtract3 est **entraîné pour l’extraction structurée**, pas pour le chat
   - Benchmarks publics et retours terrain : meilleure précision champs/métadonnées que des pipelines OCR génériques + LLM texte, avec **fraction du coût GPU**
   - Mistral OCR et similaires excellent sur la transcription ; Repody vise **l’audit métier** : champs + règles + traçabilité

4. **Astuces d’optimisation intégrées dans la plateforme**

   | Optimisation | Bénéfice |
   |--------------|----------|
   | **Quantisation Q4_K_M** | Modèle ~4B utilisable sur GPU modeste ou CPU Vulkan |
   | **Cache Redis extraction** | Clé = empreinte contenu + schéma + profil inférence ; TTL 24h ; évite de rappeler le VLM |
   | **Extraction structurée native** | Pas de parsing Markdown intermédiaire ; JSON validé Pydantic |
   | **Contrat NuExtract figé en code** | DPI, température 0.2, thinking off — reproductibilité prod |
   | **Warmup VLM** | Réduit le cold start GPU au démarrage workers |
   | **Progress batching** | Commits DB toutes les ~400 ms — moins de charge Postgres |
   | **Pools workers séparés** | `extract` (GPU/VLM) vs `fast` (règles sans fichier) — scaling indépendant |
   | **Extraction parallèle** | Multi-documents dans un même run en parallèle |

---

### PARTIE 3 — Repody : la plateforme et ses fonctionnalités (5–6 min)

Présente Repody comme **plateforme d’agents**, pas juste un modèle.

**Flux métier end-to-end :**
1. L’utilisateur configure un **Workflow** (documents, schéma de champs, exemples ICL, règles)
2. Il **déploie** le workflow (clé API production)
3. Il soumet des fichiers → création d’un **Run**
4. Traitement **asynchrone** : workers Taskiq + Redis Streams
5. Extraction VLM → **validation règles** (logique + LLM texte séparé si besoin)
6. Revue dans l’UI : champs, violations, export, dashboard

**Fonctionnalités clés à mentionner :**

| Domaine | Capacités |
|---------|-----------|
| **Workflow builder** | Schémas, règles logiques (`simpleeval`), règles LLM en langage naturel, validation cross-documents |
| **Ingestion** | Upload presigné MinIO/S3, sniff MIME, PDF/images, limite 25 MB |
| **Exécution** | Runs test (builder) + runs production (API), SSE progression + fallback poll |
| **Règles** | Logic rules déterministes + LLM rules sur modèle texte **séparé** du VLM |
| **Revue** | Liste audits, détail run, dashboard KPIs, export |
| **Admin / opérateur** | Catalog modèles, probes live, benchmarks intégrés, diagnostics plateforme |
| **IAM** | Keycloak OIDC + matrice permissions UI |

**Architecture (schéma mental simple) :**
```
Next.js UI → Keycloak → FastAPI /v1 → Postgres + Redis + MinIO
                                      ↓
                              Taskiq workers → llama-server (NuExtract3)
```

**Bounded contexts (optionnel pour public technique) :**
- Configuration workflow
- Exécution audit (cœur — domain events RunQueued/Started/Completed/Failed)
- Plateforme / catalog

---

### PARTIE 4 — Production-ready : sécurité, observabilité, résilience (4–5 min)

Insiste sur ce qui distingue un POC d’une plateforme enterprise :

**Sécurité & gouvernance**
- **OIDC Keycloak** : JWT, refresh, rôles realm
- **Casbin RBAC** : rôles `viewer` / `operator` / `admin` / `platform_admin` ; permissions par ressource (workflow, run, audit, upload, metrics, operator…)
- **Double auth sur les runs** : JWT admin OU clé API workflow (hash SHA-256, compare timing-safe)
- Upload : allowlist MIME, sanitization noms, validation Pydantic
- **Rate limiting Redis** : 300 req/min/IP global + limites par workflow/client sur création de runs
- **Fail-closed** en prod si Redis indisponible (`AUDIT_RATE_LIMIT_FAIL_CLOSED`)
- Secrets via **Vault + External Secrets Operator** (jamais en clair dans Helm)
- K8s : NetworkPolicy, non-root, PDB, HPA, scan CI (Trivy, Grype, pip-audit)

**File d’attente & admission**
- **Taskiq + Redis Streams** : découplage API ↔ workers
- **Admission control** : cap profondeur file → HTTP 503 + `Retry-After` si surcharge
- **Outbox Postgres** avant enqueue Taskiq : pas de run perdu si Redis transient down
- **Replay** dispatch jusqu’à 8 tentatives
- Maintenance : runs stale, timeouts queued (60 min), claiming atomique advisory locks
- Domain layer Run : transitions d’état validées (queued → running → done/failed)

**Observabilité**
- **structlog** JSON + corrélation traces OTEL
- Stack locale : **Grafana + Loki + Tempo + OTEL Collector + Bugsink**
- Prod : OTLP client-side, logs redacted (pas de tokens/mots de passe)
- Healthz readiness : profondeur file, probes inférence optionnelles
- Benchmarks operator : latence queue, extraction, cache hit, accuracy

**Déploiement**
- Dev : Docker Compose (Postgres, Redis, MinIO, Keycloak, workers)
- Prod : Helm modulaire (`control` / `workers` / `data` / `auth`), OpenShift-ready
- Inférence **toujours externe** au chart app (ADR 005) — souveraineté GPU client

---

### PARTIE 5 — Synthèse & messages de clôture (1–2 min)

**3 messages à retenir :**

1. **Ne pas généraliser l’IA** — utiliser un VLM **petit (≤4B), quantifié, spécialisé extraction**, pas un LLM générique + OCR en cascade.

2. **Single-pass beats pipeline** — PDF/image → JSON direct avec NuExtract3 bat la latence, le coût et la fragilité du PDF→Markdown→LLM.

3. **Repody = plateforme complète** — workflows, règles, queue, sécurité Casbin, rate limiting, observabilité, déploiement K8s — pas un script Jupyter.

**Call to action :**
- Démo live : créer un workflow facture → upload PDF → voir extraction + règle “montant TTC > 0” → dashboard
- Ou : benchmark operator montrant cache hit vs cold extraction

---

### Contraintes de rédaction

- Utilise des **exemples métier** (facture fournisseur, contrat, conformité TVA/IBAN).
- Inclus **1 diagramme de séquence simplifié** (upload → queue → worker → VLM → règles → UI).
- Inclus **1 tableau comparatif** : Pipeline OCR classique vs Repody single-pass.
- Évite les chiffres de benchmark inventés ; si tu cites NuExtract vs Mistral OCR, dis “benchmarks publics numind / retours terrain” ou laisse un placeholder [INSÉRER CHIFFRE].
- Termine par une slide “Stack” : Next.js 16, FastAPI, Taskiq, Redis, Postgres, MinIO, Keycloak, Casbin, NuExtract3-GGUF Q4_K_M, llama-server.
```

---

## Variante courte (pitch 5 min)

Ajouter à la fin du prompt :

```
Version courte : 5 slides max — Problème IA gourmande → OCR pipeline vs single-pass NuExtract3 → Demo Repody → Sécurité/queue/obs → Pourquoi maintenant.
```

---

## Démo live (optionnel)

```powershell
pnpm dev:all          # stack Compose + API + UI
# http://localhost:3000 — Keycloak admin/admin
# Workflow builder → Test tab → upload facture PDF → voir SSE progression
```

---

## Références internes

| Sujet | Doc |
|-------|-----|
| Architecture | [CONTEXT.md](../CONTEXT.md) |
| Inventaire plateforme | [PLATFORM-INVENTORY.md](./PLATFORM-INVENTORY.md) |
| Inférence NuExtract3 | [REPODY-VLM.md](./REPODY-VLM.md) |
| Benchmarks | [BENCHMARKING.md](./BENCHMARKING.md) |
| Diagramme séquence | [diagrams/sequence-cycle-vie-complet.mmd](./diagrams/sequence-cycle-vie-complet.mmd) |
