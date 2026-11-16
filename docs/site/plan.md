# repody.com: plan

The public site that sells Repody: a document audit platform bought outright, installed on the
client's own infrastructure, under the client's own brand. It also shows how the product is built,
end to end, because the buyers (and their engineering and security teams) decide on that.

## Who reads it, and what they must leave with

| Reader | Arrives with | Leaves knowing |
|---|---|---|
| Head of operations, back office (bank, insurer, telco) | Teams retype invoices, statements, claims, contracts | Repody reads them, checks them against their rules, and shows what to review |
| CIO, CTO, architect | "Can we run it ourselves, and will it scale?" | One server or Kubernetes/OpenShift, their GPU or a managed one, documented, observable |
| CISO, compliance (CNDP, Bank Al-Maghrib, ACAPS, ANRT expectations) | "Where does the data go, who can see it?" | Nowhere outside their infrastructure; SSO, roles, MFA, hardened and signed images |
| Procurement, partner, integrator | "Can we resell it under our name?" | White label from six settings; licence, not subscription |
| An engineer evaluating the build | "Is this real engineering?" | Every gate, scan, signature and runbook, with specifics |

Market: Morocco first. French is the default language, English second. Arabic is a later addition
(needs RTL review of every layout, not a translation pass).

## Positioning

**Repody reads your documents, checks them against your rules, and runs on your servers.**

Three claims carry the site, each proven on a page:

1. **Accurate structured extraction in one pass.** A specialised vision model (NuExtract3) reads the
   page image straight into typed fields: no OCR, no Markdown, no second model guessing.
2. **Your rules, applied to every document.** Checks within a document and across documents, with a
   verdict a person can act on: passed, needs review, rejected.
3. **Yours to run and to brand.** On-premises or private cloud, behind your SSO, under your name.

## Site map

| Path (under `/fr/` and `/en/`) | Page | Job |
|---|---|---|
| `/fr/`, `/en/` | Home | The story in one scroll; routes each reader to their page |
| `platform/` | Platform | Every product capability, screen by screen |
| `security/` | Security | Identity, data sovereignty, application, supply chain, infrastructure |
| `architecture/` | Architecture | Components, data flow, model serving, scale, resilience, observability |
| `deployment/` | Deployment and white label | Topologies, what is in the box, branding, the install path |
| `engineering/` | Engineering (DevSecOps) | CI/CD, quality gates, signing, release, operations |
| `solutions/banks/` | Banks | Use cases, documents, rules, compliance posture |
| `solutions/insurance/` | Insurance | idem |
| `solutions/telecom/` | Telecom | idem |
| `contact/` | Demo request | One form, what happens next |
| `legal/`, `privacy/` | Legal | Required, short |

The same paths in both languages keep the language switch a one-segment swap; `/` sends readers to `/fr/`.

Plus `sitemap.xml`, `robots.txt`, `llms.txt` (and `llms-full.txt`), Open Graph images (`/og/fr.png`, `/og/en.png`), JSON-LD, and one bilingual 404.

## Home, section by section

1. **Hero.** Headline (the positioning line), one sentence, two actions (request a demo, see the
   platform). The bright element: a real run, replayed: the timeline steps through "GPU waking up",
   extraction, rules, then the verdict with its fields. It is the product's own moment, not a decoration.
2. **Proof strip.** Facts, not logos (no client names yet): "1 pass from page to fields",
   "24 field types", "99 pages per document", "0 data leaving your network".
3. **Video.** A 16:9 frame with a poster from the real UI and a play control; the video slot is a
   single setting, filled later (HyperFrames).
4. **How it works.** Four steps on one line that draws as it scrolls into view: describe the documents,
   write the rules, send files (UI or API), review the verdict.
5. **The old way vs Repody.** OCR → Markdown → LLM (three failure points) against one pass.
6. **Platform tour.** Three large real screenshots with captions (builder, report, overview), each
   linking to its part of `platform/`.
7. **White label, live.** A brand switcher: pick a client palette, the product screenshot frame
   re-themes in place (the theme engine runs in the page). The point is shown, not claimed.
8. **Security and sovereignty.** Six facts with one line each, link to `security/`.
9. **Deployment.** Three topologies side by side, link to `deployment/`.
10. **Built like infrastructure.** The CI/CD pipeline as a row of gates lighting up in order, link to
    `engineering/`.
11. **Industries.** Banks, insurance, telecom: the documents each one receives.
12. **FAQ.** Eight real questions (data location, GPU needs, languages, accuracy, licence, integration).
13. **Final call.** One sentence, one button.

## The other pages (structure)

- **Platform:** builder (documents, 24 field types (each simple type also as a list), nested objects and tables, NuExtract template
  import), rules (10 operators, arithmetic, table aggregates, one or two documents, reject or flag),
  runs (UI tests, API with per-workflow keys, live progress with the model warm-up step, queue
  position), reports (field ledger, rule notes, raw model output, print, CSV), overview, command
  palette, two languages, light and dark, keyboard first.
- **Security:** Keycloak OIDC with PKCE, TOTP MFA, four roles and six permissions,
  workflow API keys stored as SHA-256 and compared in constant time, upload type and size limits,
  rate limits and queue admission (429/503 with Retry-After), run retention purge; containers
  non-root, read-only, no-new-privileges, memory-capped, digests pinned; zero published ports
  (Cloudflare Tunnel), admin console behind Cloudflare Access, server reachable only over a private
  network (Tailscale) with identity-based SSH; images scanned (Trivy), SBOM and provenance attached,
  signed with Sigstore cosign and verified before every deploy.
- **Architecture:** Next.js web, FastAPI API, Hatchet workers, PostgreSQL,
  S3-compatible storage (SeaweedFS), Keycloak; the model server is external (vLLM, OpenAI-compatible):
  your GPU or a managed serverless GPU that sleeps when idle and wakes from a memory snapshot.
  Extraction: 170 DPI rasterisation, up to 99 pages per request, result cache keyed by content and
  schema, bounded concurrency. Resilience: atomic run claiming, timeouts and failures handled by Hatchet,
  maintenance loop. Observability: structured JSON logs, OpenTelemetry traces, Prometheus, Grafana,
  Loki, Tempo, error tracking.
- **Deployment:** single server (Docker Compose, every container memory-capped, 6.5 GB of limits in total), Kubernetes
  or OpenShift (Helm chart: HPA, PDB, NetworkPolicies, migrations job; CloudNativePG with pooler and
  scheduled backups; External Secrets with Vault; Argo CD application), managed GPU or your own.
  White label: name, logo, base colour, accent, contrast, radius; contrast guaranteed by the engine.
- **Engineering:** every gate of CI in order (path-filtered jobs, Ruff, Pyright, import-linter layer
  contracts, Pytest on a real Postgres with Alembic, OpenAPI drift both ways, Biome, ESLint, Vitest,
  knip dead code, deploy checks, link checks, production build, full-stack container boot),
  security workflow (Trivy filesystem and image scans to code scanning), release (Bake, SBOM,
  provenance, cosign keyless), deploy (workflow identity federation to the private network, signature
  verification, health-gated rollout, public check), Dependabot on every ecosystem with digests
  pinned, runbooks and documentation checked in CI.

## Design

The product's direction, applied to a marketing page (see `.interface-design/system.md`): the same
theme engine and tokens, Inter, the status glyph as the signature. Marketing allowances: larger type
for headlines (Inter Display through optical sizing, 44 to 64 px), more air between sections, a dark
hero band that frames the product. Light by default, dark mode followed.

**Motion inventory, and nothing else moves:**

| Where | What | Why |
|---|---|---|
| Hero | The run replays: steps tick, GPU card wakes, verdict appears (loops, pauses off-screen) | Shows the product's real moment |
| How it works | The connecting line draws as the section enters, steps light in order (once) | Shows sequence |
| White label | Screenshot frame re-themes when a brand is picked | Proves the claim |
| Engineering | Pipeline gates tick in order as the section enters (once) | Shows the gate sequence |
| Everywhere | Reduced motion: no movement, cross-fades only | Accessibility |

No entrance animation on every section, no parallax, no hover lifts.

## SEO, GEO, performance

- Static export; every page pre-rendered; `hreflang` fr/en/x-default; canonical per page; per-page
  title and description written for the query (fr: « audit documentaire », « extraction de données
  factures », « plateforme on-premise », « marque blanche »).
- JSON-LD: Organization, SoftwareApplication (with feature list), FAQPage, BreadcrumbList.
- GEO: `llms.txt` and `llms-full.txt` with the facts in plain sentences; each page opens with a
  self-contained summary paragraph a model can quote; numbers stated with units; terms defined once.
- Performance budget: LCP under 1.8 s on 4G, CLS 0; images AVIF/WebP with sizes, fonts self-hosted
  via next/font, JS only where something moves (Motion islands).
- Accessibility: WCAG 2.2 AA, keyboard paths, focus visible, reduced motion.

## Critique of this plan, and the changes made

- *Risk: a feature dump.* A list of 150 items convinces no one. Change: each page leads with what it
  changes for the reader, then the specifics grouped under it; the specifics stay (the user wants the
  depth), but as evidence under a claim.
- *Risk: compliance claims.* Repody is not certified by CNDP, BAM, ACAPS or ANRT. Change: the site
  says what the architecture enables (data stays on your servers, access is audited by your IdP),
  never "compliant" or "certified".
- *Risk: fake proof.* No client logos, no invented accuracy percentages. Change: the proof strip
  uses facts of the product only; accuracy is described as measured on your documents during a pilot.
- *Risk: the presentation's outdated facts* (quantised GGUF, MinIO, Vault-only secrets, LLM rules,
  Casbin, SSE). Change: everything is taken from the current code and docs; the deck is context only.
- *Risk: screenshots with test data.* Change: screenshots are captured from a clean demo dataset.
- *Risk: Arabic expected in Morocco.* Change: noted as phase 2 with a proper RTL pass.
