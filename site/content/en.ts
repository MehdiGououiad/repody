import type { Dict } from "./fr";

/** English: same structure as the French content. */
export const en: Dict = {
  lang: "en",
  languageName: "English",
  common: {
    skip: "Skip to content",
    nav: {
      platform: "Platform",
      security: "Security",
      architecture: "Architecture",
      deployment: "Deployment",
      engineering: "Engineering",
      solutions: "Industries",
      banks: "Banking",
      insurance: "Insurance",
      telecom: "Telecom",
    },
    demo: "Request a demo",
    playground: "Try the playground for free",
    playgroundShort: "Playground",
    seePlatform: "See the platform",
    learnMore: "Learn more",
    menu: "Menu",
    close: "Close",
    language: "Language",
    footer: {
      tagline:
        "The document audit platform that reads your documents, checks them against your rules and runs on your servers.",
      product: "Product",
      company: "Company",
      contact: "Contact",
      legal: "Legal notice",
      privacy: "Privacy",
      rights: "All rights reserved.",
      madeIn: "Built for banks, insurers and telecom operators in Morocco.",
    },
    breadcrumbHome: "Home",
    onThisPage: "On this page",
  },

  home: {
    meta: {
      title: "Repody: on-premise, white-label document audit",
      description:
        "Repody extracts the data from your invoices, statements, contracts and files, checks it against your rules and returns a verdict. Installed on your servers, under your brand.",
    },
    hero: {
      title: "Your documents read, checked and decided, on your servers",
      lead: "Repody extracts every field from your invoices, statements and contracts in a single pass, applies your business rules and tells you what to review. You run it yourself, under your own brand.",
      note: "Perpetual licence · On-premise or private cloud · French and English",
    },
    replay: {
      label: "Live run",
      queue: "Queued",
      gpu: "GPU waking up",
      gpuDone: "GPU started",
      gpuHint: "The model resumes from a memory snapshot.",
      extract: "Extract · Invoice",
      rules: "Check 2 rules",
      save: "Save the report",
      verdict: "Rejected",
      verdictFacts: "1 of 2 rules passed · 4 fields · 2.1 s",
      fields: [
        { key: "invoice_number", value: "FAC-2026-0412", ok: true },
        { key: "supplier", value: "Atlas Logistique SARL", ok: true },
        { key: "net_amount", value: "MAD 48,500.00", ok: false },
        { key: "total", value: "MAD 58,800.00", ok: false },
      ],
      note: "Total ≠ net + 20% VAT",
      gpuTime: "6.8 s",
      extractTime: "0.4 s",
    },
    proof: [
      { value: "1", label: "pass from the document image to typed fields" },
      { value: "24", label: "field types, from dates to IBANs and tables" },
      { value: "99", label: "pages read per document" },
      { value: "0", label: "bytes of your documents leaving your network" },
    ],
    video: {
      title: "Repody in two minutes",
      caption:
        "One workflow end to end: describe the documents, write the rules, send a file, read the verdict.",
      soon: "Video coming soon",
    },
    how: {
      title: "From a pile of documents to a verdict",
      lead: "A workflow describes what you receive and what must be true. Repody does the rest, document after document.",
      steps: [
        {
          title: "Describe the documents",
          body: "Name each document you receive and the fields to read from it: exact text, amounts, dates, IBANs, lists, tables.",
        },
        {
          title: "Write the rules",
          body: "Compare fields, do arithmetic, cross-check two documents. Each rule rejects or flags.",
        },
        {
          title: "Send the files",
          body: "From the interface to test, from your systems through the API with the workflow's key.",
        },
        {
          title: "Read the verdict",
          body: "Passed, needs review or rejected, with every extracted value and the failing rule beside it.",
        },
      ],
    },
    compare: {
      title: "One pass instead of three",
      lead: "Classic pipelines turn the document into text, then Markdown, then ask a large model to guess. Every step loses information and adds time.",
      oldTitle: "Classic pipeline",
      oldSteps: ["OCR", "Markdown", "Large language model"],
      oldPoints: [
        "Three calls to pay for one document",
        "Layout and checkboxes get lost",
        "The model patches OCR errors without seeing the page",
        "Latencies add up",
      ],
      newTitle: "Repody",
      newSteps: ["Page image", "NuExtract3", "Typed fields"],
      newPoints: [
        "A specialised model reads the page image directly",
        "Output constrained by your schema: valid, typed JSON",
        "Tables, nested objects and lists understood as they are",
        "One call per document, several documents in parallel",
      ],
    },
    tour: {
      title: "What your teams use every day",
      lead: "A dense, calm interface built for operators who review hundreds of documents.",
      items: [
        {
          title: "A report for every run",
          body: "Every field on its own line with its status mark, the failing rule written beside it, the model's raw output one click away.",
          shot: "report",
          page: "platform",
          hash: "reports",
        },
        {
          title: "A no-code workflow builder",
          body: "Documents, fields and rules read like sentences. Rules are checked while you write them.",
          shot: "builder-claim",
          page: "platform",
          hash: "builder",
        },
        {
          title: "An overview that starts with what matters",
          body: "What to review first, then the week's volume and pass rate.",
          shot: "overview",
          page: "platform",
          hash: "overview",
        },
      ],
    },
    brand: {
      title: "Your brand, not ours",
      lead: "Name, logo, base colour, accent colour, contrast and corner radius: six settings, and the whole interface re-themes, light and dark. Text contrast is guaranteed by the engine whatever colour you pick.",
      pick: "Pick a brand",
      darkMode: "Dark mode",
      presets: ["Repody", "Bank", "Insurer", "Telecom"],
      mock: {
        title: "Files to review",
        rows: ["Bank statement · KYC", "Auto claim file", "Business contract"],
        status: ["Rejected", "Needs review", "Passed"],
        action: "Review",
      },
    },
    security: {
      title: "Secure and sovereign by design",
      lead: "Repody is built for regulated environments: your documents never leave your infrastructure, and every access goes through your identity provider.",
      items: [
        {
          title: "Your data stays with you",
          body: "Database, storage and model run inside your network. Nothing is sent to a third party.",
        },
        {
          title: "Your SSO, your roles",
          body: "OpenID Connect with Keycloak, PKCE, two-factor authentication and four roles with precise permissions.",
        },
        {
          title: "Protected API keys",
          body: "One key per workflow, shown once, stored as a SHA-256 hash and compared in constant time.",
        },
        {
          title: "Hardened containers",
          body: "Non-root users, read-only file systems, no privilege escalation, capped memory.",
        },
        {
          title: "Signed, verified images",
          body: "SBOM, provenance and a Sigstore signature on every release; the signature is verified before every deploy.",
        },
        {
          title: "No open ports",
          body: "Public traffic arrives through an outbound tunnel, administration through an identity-checked private network.",
        },
      ],
    },
    deploy: {
      title: "Installed where your data must stay",
      lead: "The same product, three ways to run it.",
      options: [
        {
          title: "One server",
          body: "Docker Compose on a Linux machine. The whole stack, ready in one command, deployed automatically.",
        },
        {
          title: "Kubernetes or OpenShift",
          body: "A Helm chart with autoscaling, disruption budgets and network policies.",
        },
        {
          title: "Your GPU or a managed GPU",
          body: "The model runs on your graphics card or on a serverless GPU that switches off when idle.",
        },
      ],
    },
    engineering: {
      title: "Built like critical infrastructure",
      lead: "Every change goes through a chain of checks before it reaches a server. A release ships only when every one of them is green.",
      gates: [
        "Lint and format",
        "Type checks",
        "Architecture contracts",
        "Tests on PostgreSQL",
        "API contract",
        "Dead code",
        "Build",
        "Full stack boots",
        "Vulnerability scan",
        "SBOM and provenance",
        "Signing",
        "Verify and deploy",
      ],
    },
    industries: {
      title: "Built for industries that run on documents",
      items: [
        {
          title: "Banking",
          body: "Account opening, lending, compliance.",
          docs: ["Bank statements", "Proof of income", "Bank details (RIB)", "Pro forma invoices"],
          page: "banks",
        },
        {
          title: "Insurance",
          body: "Underwriting and claims handling.",
          docs: [
            "Accident reports",
            "Garage quotes and invoices",
            "Expert reports",
            "Certificates",
          ],
          page: "insurance",
        },
        {
          title: "Telecom",
          body: "Business subscriptions, purchasing, compliance.",
          docs: [
            "Subscription contracts",
            "Purchase orders",
            "Supplier invoices",
            "Company documents",
          ],
          page: "telecom",
        },
      ],
    },
    faq: {
      title: "Frequently asked questions",
      items: [
        {
          q: "Where are our documents stored?",
          a: "On your servers. Repody installs in your infrastructure (one server or a Kubernetes cluster) with its PostgreSQL database, S3-compatible object storage and model server. No document is sent to a third-party service.",
        },
        {
          q: "Do we need a GPU?",
          a: "The extraction model runs best on a 24 GB GPU (NVIDIA L4 or A10). Use your own, or a serverless GPU that only costs while runs are processing and starts in a few seconds.",
        },
        {
          q: "Which documents and languages?",
          a: "PDF, PNG, JPEG and WebP, up to 99 pages per document and 20 files per run. The model reads French, English and the main European languages; the interface is in French and English.",
        },
        {
          q: "What accuracy should we expect?",
          a: "It depends on your documents. We measure it with you during a pilot, on your own files and rules, before any decision.",
        },
        {
          q: "Can we resell Repody under our brand?",
          a: "Yes. Name, logo and colours are set per deployment, without changing code. The licence covers white-label use.",
        },
        {
          q: "How do we integrate it?",
          a: "Through a REST API: one call sends the files and returns a run id, a second reads the result. cURL, Python and JavaScript examples are generated in the interface for every workflow.",
        },
        {
          q: "Who can see what?",
          a: "Access goes through your identity provider. Four roles (viewer, operator, admin, platform admin) grant precise permissions on workflows and runs.",
        },
        {
          q: "How do updates work?",
          a: "Every release is built, scanned, signed and published with its software bill of materials. You choose the version to deploy; its signature is verified before installation.",
        },
      ],
    },
    cta: {
      title: "See Repody on your own documents",
      lead: "A 30-minute demo, then a pilot on your files and your rules.",
    },
  },

  platform: {
    meta: {
      title: "Platform: extraction, rules, reports and API",
      description:
        "Workflow builder, 24 field types, rules on one or two documents, detailed reports, a REST API with per-workflow keys and live tracking of every run.",
    },
    hero: {
      title: "The whole platform, screen by screen",
      lead: "Repody covers the entire chain: describe the documents, write the rules, run, review, integrate. Every capability below exists in the product today.",
    },
    sections: [
      {
        id: "builder",
        title: "Workflow builder",
        lead: "A workflow describes the documents you receive, the fields to read and the rules to check. It is built without code, in three steps.",
        shot: "builder-documents",
        points: [
          {
            title: "Documents and fields",
            body: "Each document has a name and its list of fields. Cells are edited in place, like text.",
          },
          {
            title: "24 field types",
            body: "Exact or normalised text, numbers, integers, amounts, dates, times, durations, booleans, IBAN, BIC, email addresses, phone numbers, countries, languages, URLs, unit codes. Every simple type also comes as a list.",
          },
          {
            title: "Structures",
            body: "Lists of values, choices from a list (enum and multi-enum), nested objects and tables of rows with their columns.",
          },
          {
            title: "Model instructions",
            body: "Guidance specific to each document, on top of each field's description.",
          },
          {
            title: "NuExtract template import",
            body: "Paste an existing JSON template: fields, types and structures are created at once.",
          },
          {
            title: "Draft and publish",
            body: "A workflow saves as a draft; publishing creates its API key. Every run keeps the definition it used.",
          },
        ],
      },
      {
        id: "rules",
        title: "Business rules",
        lead: "A rule says what must be true. It reads as a sentence: on these documents, passes when, if it fails.",
        shot: "builder-claim",
        points: [
          {
            title: "Ten operators",
            body: "Equals, not equals, greater, greater or equal, less, less or equal, in a list, not in a list, exists, is empty.",
          },
          {
            title: "Arithmetic",
            body: "Add, subtract, multiply or divide two number fields before comparing: “net + VAT = total”.",
          },
          {
            title: "Table aggregates",
            body: "Sum of rows, sum of filtered rows, count of filtered rows: to reconcile a total with its lines.",
          },
          {
            title: "One or two documents",
            body: "A rule checks one document, or compares two documents of the same file: accident report and invoice, contract and purchase order.",
          },
          {
            title: "Reject or flag",
            body: "A failure rejects the run, or flags it for human review.",
          },
          {
            title: "Checked as you write",
            body: "Each condition shows the exact check the API will run, and errors appear before publishing.",
          },
        ],
      },
      {
        id: "runs",
        title: "Runs and live tracking",
        lead: "A run processes the files sent: extraction, rule checks, report. You watch it progress step by step.",
        shot: "builder-publish",
        points: [
          {
            title: "Tests from the builder",
            body: "Drop one file per document and run the workflow as it is on screen, without publishing it.",
          },
          {
            title: "Live timeline",
            body: "Queue and position, model start, each document's extraction, rules, saving: every step with its duration.",
          },
          {
            title: "GPU start made visible",
            body: "When the model was asleep, the step says so and shows the usual duration, instead of a silent wait.",
          },
          {
            title: "Documents in parallel",
            body: "A run's documents are extracted at the same time, within the limit set for the model server.",
          },
          {
            title: "Clear limits",
            body: "20 files and 25 MB per file by default, types checked (PDF, PNG, JPEG, WebP), a maximum duration per run.",
          },
          {
            title: "Cached results",
            body: "Optional: the same file with the same schema skips the model (SHA-256 key of content and schema).",
          },
        ],
      },
      {
        id: "reports",
        title: "Reports",
        lead: "The report says what happened in one line, then shows every value and every rule.",
        shot: "report",
        points: [
          {
            title: "A readable verdict",
            body: "Passed, needs review or rejected, with the rules passed, fields extracted, duration and source.",
          },
          {
            title: "Fields as a ledger",
            body: "Every field on its line with its mark: found, not found, failed. The rule at fault is written beside the value.",
          },
          {
            title: "Detailed rules",
            body: "Failures first, with their severity, the evaluated expression and the explanation.",
          },
          {
            title: "Raw model output",
            body: "The JSON returned by the model, as preview or source, ready to copy.",
          },
          {
            title: "Print and export",
            body: "Clean printing to PDF and CSV export of one report or a whole filtered list.",
          },
          {
            title: "Truncated pages flagged",
            body: "If a document exceeds the page limit, the report says how many were read.",
          },
        ],
      },
      {
        id: "api",
        title: "Integration API",
        lead: "Your systems send documents and read verdicts through a REST API. The interface generates the examples for every workflow.",
        shot: null,
        points: [
          {
            title: "Two calls",
            body: "POST sends the files and answers 202 with the run id; GET reads its state, then its report.",
          },
          {
            title: "One key per workflow",
            body: "The key only reaches its workflow and its runs, nothing else.",
          },
          {
            title: "Ready examples",
            body: "cURL, Python and JavaScript, with the workflow's address and key, copied in one click.",
          },
          {
            title: "Controlled throughput",
            body: "Runs per minute per client (429), a capped queue (503), both with Retry-After.",
          },
          {
            title: "Typed contract",
            body: "OpenAPI specification generated from the code and checked in CI; the interface derives its types from it.",
          },
          {
            title: "Try it from the interface",
            body: "Start a run with the real key, exactly like an API client.",
          },
        ],
      },
      {
        id: "overview",
        title: "Overview",
        lead: "The home page starts with what needs a person.",
        shot: "overview",
        points: [
          { title: "Needs review", body: "Runs whose rules failed, oldest first." },
          {
            title: "The week in numbers",
            body: "Runs, pass rate and rule failures, compared with the previous week.",
          },
          { title: "Volume per day", body: "Each day leads to its runs." },
          {
            title: "Queue status",
            body: "Runs in progress and waiting, an alert if a run stops responding.",
          },
        ],
      },
      {
        id: "experience",
        title: "An interface for daily work",
        lead: "Every detail serves operators who spend their day in the tool.",
        shot: "workflows",
        points: [
          {
            title: "Command palette",
            body: "⌘K or / to jump to any workflow, recent run or page, and to create a workflow.",
          },
          {
            title: "Two languages",
            body: "French and English, local date and number formats, the reader's time zone.",
          },
          {
            title: "Light, dark or system",
            body: "The theme follows your choice or your computer's.",
          },
          {
            title: "Keyboard first",
            body: "Keyboard navigation, visible focus, checked contrast, reduced motion when your system asks for it.",
          },
          { title: "Mobile", body: "Every page stays usable on a phone." },
          {
            title: "Bulk delete",
            body: "Select several workflows and archive them together, with confirmation.",
          },
        ],
      },
    ],
    typesTitle: "The 24 field types",
    operatorsTitle: "Operators and arithmetic",
    operatorsLead: "What a condition can check, and what it can calculate before comparing.",
    operators: [
      { symbol: "==", label: "equals" },
      { symbol: "!=", label: "does not equal" },
      { symbol: ">", label: "greater than" },
      { symbol: ">=", label: "greater than or equal to" },
      { symbol: "<", label: "less than" },
      { symbol: "<=", label: "less than or equal to" },
      { symbol: "IN", label: "in the list" },
      { symbol: "NOT_IN", label: "not in the list" },
      { symbol: "EXISTS", label: "present" },
      { symbol: "IS_EMPTY", label: "empty" },
    ],
    computeTitle: "Calculations",
    compute: [
      { symbol: "+ − × ÷", label: "between two numeric fields" },
      { symbol: "sum_rows", label: "sum of a table column" },
      { symbol: "sum_rows_where", label: "sum of the rows that meet a condition" },
      { symbol: "count_rows_where", label: "number of rows that meet a condition" },
    ],
    listNote: "Every simple type also comes as a list: several dates, several amounts.",
    apiExample: {
      title: "Two calls",
      send: "Send the files",
      read: "Read the verdict",
    },
  },

  security: {
    meta: {
      title: "Security: identity, sovereignty, software supply chain",
      description:
        "Keycloak OIDC with MFA, roles and permissions, hashed API keys, hardened containers, no open ports, signed and verified images: Repody's security in detail.",
    },
    hero: {
      title: "Security is not a product option",
      lead: "Repody handles sensitive documents: statements, contracts, identity papers. Every layer is designed so this data stays with you and is seen only by the right people.",
    },
    posture:
      "Repody gives you the technical means to meet your obligations (Law 09-08 and the CNDP, Bank Al-Maghrib, ACAPS or ANRT requirements): data hosted with you, access controlled by your identity provider, traceability. Compliance of your processing remains your responsibility; Repody is not certified by these authorities.",
    groups: [
      {
        id: "identity",
        title: "Identity and access",
        points: [
          {
            title: "OpenID Connect",
            body: "Sign-in with Keycloak (or your OIDC provider), authorization code flow with PKCE S256.",
          },
          {
            title: "Two-factor authentication",
            body: "TOTP required for the admin account from the first sign-in, password changed immediately.",
          },
          {
            title: "Four roles, six permissions",
            body: "Viewer, operator, admin and platform admin; read, edit and delete workflows, read and start runs, see metrics.",
          },
          {
            title: "Checked on every call",
            body: "Every API request verifies the token (issuer, audience, signature) and the permission it needs.",
          },
          {
            title: "Safe session refresh",
            body: "Tokens are refreshed on the server; simultaneous requests share a single refresh.",
          },
          {
            title: "Isolated admin console",
            body: "The Keycloak console has its own hostname behind Cloudflare Access; the public domain only exposes the application realm.",
          },
        ],
      },
      {
        id: "application",
        title: "Application",
        points: [
          {
            title: "Per-workflow API keys",
            body: "Shown once, stored as a SHA-256 hash, compared in constant time; they only start and read their own workflow's runs.",
          },
          {
            title: "Checked uploads",
            body: "File count, size and type verified on entry; private object storage.",
          },
          {
            title: "Controlled throughput",
            body: "A per-client limit (HTTP 429) and a capped queue (HTTP 503), with Retry-After.",
          },
          {
            title: "Retention",
            body: "Runs older than the chosen period are purged automatically, in batches.",
          },
          {
            title: "Logs without secrets",
            body: "Structured JSON logs, without tokens or passwords.",
          },
          {
            title: "Errors that don't leak",
            body: "Errors returned to clients describe the problem, never the system's internals.",
          },
        ],
      },
      {
        id: "infrastructure",
        title: "Infrastructure",
        points: [
          {
            title: "Hardened containers",
            body: "Non-root users, read-only root file systems, no privilege escalation, capped memory for every service.",
          },
          {
            title: "No public ports",
            body: "Web traffic arrives through an outbound Cloudflare tunnel; the firewall only accepts the private admin network.",
          },
          {
            title: "Identity-checked admin access",
            body: "SSH over Tailscale: access granted by policy, tested automatically, no shared keys.",
          },
          {
            title: "Deploys without standing secrets",
            body: "The deploy pipeline authenticates through identity federation (OIDC), not a stored key.",
          },
          {
            title: "Kubernetes",
            body: "Network policies, disruption budgets, external secrets (External Secrets with Vault).",
          },
          {
            title: "System updates",
            body: "Automatic security updates on the server, base images tracked and updated.",
          },
        ],
      },
      {
        id: "supply-chain",
        title: "Software supply chain",
        points: [
          {
            title: "Vulnerability scanning",
            body: "Trivy scans the code and every image; a high or critical finding blocks the release.",
          },
          {
            title: "SBOM and provenance",
            body: "Every published image carries its software bill of materials and provenance attestation.",
          },
          {
            title: "Sigstore signing",
            body: "Images are signed keylessly (cosign, OIDC identity) and the signature is verified before every deploy and promotion.",
          },
          {
            title: "Pinned dependencies",
            body: "Images by digest, CI actions by commit; Dependabot proposes every update.",
          },
          {
            title: "Central results",
            body: "Scan results are published to the repository's security tab (SARIF).",
          },
          {
            title: "Immutable releases",
            body: "A release is a tag and a set of signed images; you deploy a release, not a branch.",
          },
        ],
      },
    ],
  },

  architecture: {
    meta: {
      title: "Architecture: components, model, scaling",
      description:
        "Next.js, FastAPI, Taskiq workers on Redis Streams, PostgreSQL, S3 storage, Keycloak and an external vLLM model server: Repody's architecture and how it scales.",
    },
    hero: {
      title: "A simple architecture, built to last",
      lead: "Standard components, each in its place: an interface, an API, workers, a database, storage, an identity provider and a model server you control.",
    },
    diagram: {
      user: "Operators",
      client: "Your systems",
      web: "Web interface",
      webTech: "Next.js",
      api: "API",
      apiTech: "FastAPI",
      workers: "Workers",
      workersTech: "Taskiq · Redis Streams",
      db: "Database",
      dbTech: "PostgreSQL",
      storage: "Object storage",
      storageTech: "S3-compatible",
      idp: "Identity",
      idpTech: "Keycloak · OIDC",
      model: "Model server",
      modelTech: "vLLM · NuExtract3",
      userTech: "Browser",
      clientTech: "REST · API key",
    },
    groups: [
      {
        id: "components",
        title: "Components",
        points: [
          {
            title: "Web interface",
            body: "Server-rendered Next.js; every request goes through a proxy that attaches the user's token.",
          },
          {
            title: "API",
            body: "FastAPI, typed end to end, separate and enforced layers (API, application, extraction, rules, infrastructure).",
          },
          {
            title: "Workers",
            body: "Taskiq on Redis Streams: the API answers at once, workers process runs in the background.",
          },
          {
            title: "PostgreSQL",
            body: "Workflows, runs, fields and rule results; Alembic migrations applied by a dedicated service before start-up.",
          },
          {
            title: "Object storage",
            body: "Uploaded files, in S3-compatible storage (SeaweedFS included, or your own).",
          },
          {
            title: "Keycloak",
            body: "Optimised image, production realm built in, settings injected at start-up.",
          },
        ],
      },
      {
        id: "model",
        title: "The extraction model",
        points: [
          {
            title: "NuExtract3",
            body: "A vision model specialised in structured extraction: it receives the page images and a JSON template, and returns the fields.",
          },
          {
            title: "Served by vLLM",
            body: "OpenAI-compatible API, speculative decoding, full weights; the model server stays outside the product, on your GPU or a managed one.",
          },
          {
            title: "Pages at 170 DPI",
            body: "Each page is rendered at the resolution the model expects, up to 99 pages per document.",
          },
          {
            title: "GPU on demand",
            body: "In managed mode, the GPU switches off after a minute without requests and resumes from a memory snapshot in seconds; one container at most.",
          },
          {
            title: "Start-up announced",
            body: "Before extracting, the worker checks whether the model is awake; if not, the run shows “GPU waking up”.",
          },
          {
            title: "Measured",
            body: "Warm model call: about 0.4 s for a one-page invoice; cold start: about 7 s.",
          },
        ],
      },
      {
        id: "scale",
        title: "Scale and resilience",
        points: [
          {
            title: "Independent workers",
            body: "Add workers without touching the API; on Kubernetes, the API and workers autoscale (HPA).",
          },
          {
            title: "Atomic claiming",
            body: "A run is processed once, even when several workers receive it.",
          },
          {
            title: "Timeouts and recovery",
            body: "Every run has a maximum duration; a maintenance task closes runs whose worker stopped.",
          },
          {
            title: "Admission control",
            body: "Past the chosen queue depth, the API refuses cleanly (503) instead of collapsing.",
          },
          {
            title: "Bounded concurrency",
            body: "Simultaneous requests to the model are capped so the GPU is never overloaded.",
          },
          {
            title: "Highly available PostgreSQL",
            body: "On Kubernetes: CloudNativePG with a connection pooler and scheduled backups.",
          },
        ],
      },
      {
        id: "observability",
        title: "Observability",
        points: [
          {
            title: "Structured logs",
            body: "JSON, each line carrying the id of the run concerned.",
          },
          {
            title: "Traces",
            body: "OpenTelemetry from the API to the workers, collected by an OpenTelemetry Collector.",
          },
          {
            title: "Full stack included",
            body: "Prometheus, Grafana, Loki, Tempo and Alloy, configured.",
          },
          {
            title: "Error tracking",
            body: "Interface and server errors reported to a Sentry-compatible service you can host yourself.",
          },
          {
            title: "Health probes",
            body: "Separate liveness and readiness, so the orchestrator knows when to restart and when to wait.",
          },
          {
            title: "Operations view",
            body: "Stuck runs flagged in the interface, live queue status.",
          },
        ],
      },
    ],
    flow: {
      title: "The life of a run",
      lead: "From the file received to the verdict, what happens at each step.",
      steps: [
        {
          title: "Intake",
          body: "The API checks the key or token, then the number, size and type of the files, stores them in object storage and answers 202.",
        },
        {
          title: "Queue",
          body: "The run enters Redis Streams. When the queue is full, the API answers 503 with Retry-After.",
        },
        {
          title: "Claim",
          body: "A worker claims it atomically, checks that the model is awake and starts it if needed.",
        },
        {
          title: "Extraction",
          body: "Each page becomes an image at 170 DPI; the documents go to the model in parallel, each with its JSON template.",
        },
        {
          title: "Rules",
          body: "The engine evaluates every rule on the extracted values, within a document or across two.",
        },
        {
          title: "Report",
          body: "Fields, rules and verdict are stored in PostgreSQL; the interface and the API read them.",
        },
      ],
    },
    decisions: {
      title: "Written decisions",
      lead: "Every architecture choice has its record in the repository, with the context and the alternatives set aside.",
      items: [
        {
          adr: "001",
          title: "Asynchronous runs with Taskiq",
          body: "The API answers at once; workers process on Redis Streams.",
        },
        {
          adr: "004",
          title: "Cloud and Kubernetes packaging",
          body: "A Helm chart and manifests for customers' clusters.",
        },
        {
          adr: "005",
          title: "External inference",
          body: "The model server stays outside the chart: your GPU or a managed one.",
        },
        {
          adr: "009",
          title: "A simple backend",
          body: "One definition, one queue, one upload path.",
        },
        {
          adr: "010",
          title: "Explicit lifecycles",
          body: "Every state of a workflow and a run, and its transitions, has a name.",
        },
      ],
    },
  },

  deployment: {
    meta: {
      title: "On-premise deployment and white label",
      description:
        "Repody installs on one server with Docker Compose or on Kubernetes and OpenShift with Helm, with your GPU or a managed one, under your brand.",
    },
    hero: {
      title: "On your servers, under your name",
      lead: "Repody is licensed and installed in your infrastructure. You keep the data, the access, the versions and the brand.",
    },
    options: [
      {
        id: "server",
        title: "One server",
        body: "To start fast or for moderate volumes.",
        points: [
          "Docker Compose: interface, API, workers, PostgreSQL, Redis, storage, Keycloak, tunnel",
          "Every service with its health check and memory limit",
          "Migrations applied automatically before start-up",
          "Deployed by the CI pipeline, signature verified, rollback in one command",
        ],
      },
      {
        id: "kubernetes",
        title: "Kubernetes or OpenShift",
        body: "For high availability and large volumes.",
        points: [
          "Helm chart: API, interface, workers, migration job, ingress",
          "Autoscaling, disruption budgets, network policies",
          "CloudNativePG with pooler and scheduled backups",
          "External secrets with Vault, Argo CD application included",
        ],
      },
      {
        id: "gpu",
        title: "The model, wherever you want",
        body: "The model server is separate from the product.",
        points: [
          "Your GPU: vLLM or any OpenAI-compatible server",
          "Managed serverless GPU: billed by the second, off when idle",
          "One address and key setting on the Repody side",
          "The product works the same either way",
        ],
      },
    ],
    brand: {
      title: "White label",
      lead: "Six variables per deployment are enough. The theme engine derives every shade of the interface from your colours, light and dark, and checks contrast.",
      vars: [
        { name: "REPODY_BRAND_NAME", body: "The product name shown everywhere" },
        {
          name: "REPODY_BRAND_LOGO_URL",
          body: "Your logo, in the sidebar and on the sign-in page",
        },
        { name: "REPODY_BRAND_BASE", body: "The neutral colour that tints surfaces and text" },
        { name: "REPODY_BRAND_ACCENT", body: "The colour of actions, focus and selection" },
        { name: "REPODY_BRAND_CONTRAST", body: "From 30 (soft) to 100 (crisp)" },
        { name: "REPODY_BRAND_RADIUS", body: "Corner radius, 0 to 12 px" },
      ],
      guarantee:
        "Text stays readable whatever the colour: the engine targets WCAG AA and darkens an accent that is too light rather than make a button unreadable; this is tested automatically on very different brands.",
    },
    box: {
      title: "What you get",
      items: [
        "The interface, API and Keycloak images, signed",
        "The production Docker Compose file and its configuration template",
        "The Helm chart and production value examples",
        "CloudNativePG, External Secrets and Argo CD manifests",
        "The observability configuration (Prometheus, Grafana, Loki, Tempo)",
        "The model server, ready to deploy",
        "Installation, operations and troubleshooting documentation",
        "Architecture decision records and the migration guide",
      ],
    },
    steps: {
      title: "The installation path",
      items: [
        {
          title: "Prepare the server",
          body: "Docker from its official repository, automatic updates, a deploy user.",
        },
        {
          title: "Connect the network",
          body: "Private admin network, a tunnel for public traffic, firewall closed.",
        },
        {
          title: "Fill in the secrets",
          body: "One .env file: passwords, addresses, brand. Nothing is written in code.",
        },
        {
          title: "Deploy a release",
          body: "The pipeline verifies the signature, sends the configuration, starts and waits until everything is healthy.",
        },
        {
          title: "First sign-in",
          body: "The admin changes the password and turns on two-factor authentication.",
        },
      ],
    },
  },

  engineering: {
    meta: {
      title: "Engineering and DevSecOps",
      description:
        "Complete continuous integration, security scans, SBOM, provenance, Sigstore signing and verified deployment: how Repody is built, tested and shipped.",
    },
    hero: {
      title: "How Repody is built and shipped",
      lead: "A product is only as good as the way it changes. Every change goes through a chain of automatic checks; every release is built, scanned, signed, verified and then deployed.",
    },
    stages: [
      {
        id: "ci",
        title: "Continuous integration",
        lead: "On every change, only the touched parts are checked, but completely.",
        gates: [
          { name: "Change detection", detail: "Jobs only run for the code that changed." },
          { name: "Ruff", detail: "Formatting and linting of the Python backend." },
          { name: "Pyright", detail: "Strict static typing of the backend." },
          {
            name: "Architecture contracts",
            detail: "import-linter checks that each layer only imports what it is allowed to.",
          },
          {
            name: "Pytest",
            detail: "Unit and integration tests on a real PostgreSQL, Alembic migrations included.",
          },
          {
            name: "API contract",
            detail:
              "The OpenAPI specification is regenerated and compared; so are the interface's types.",
          },
          { name: "Biome and ESLint", detail: "Formatting and linting of the interface." },
          { name: "TypeScript", detail: "Strict typing of the interface." },
          { name: "Vitest", detail: "Interface tests, including the theme engine's contrast." },
          { name: "knip", detail: "No unused file, export or dependency." },
          {
            name: "Deployment checks",
            detail: "Helm chart, kustomize, bake and Compose validated; docs and links checked.",
          },
          {
            name: "Build and boot",
            detail: "The images are built and the whole stack starts in containers.",
          },
        ],
      },
      {
        id: "security",
        title: "Security",
        lead: "A dedicated pipeline scans the code and the images.",
        gates: [
          { name: "Trivy, repository", detail: "Dependencies, secrets and configuration scanned." },
          { name: "Trivy, images", detail: "Every built image is scanned." },
          { name: "Blocking", detail: "A high or critical vulnerability fails the pipeline." },
          { name: "Code scanning", detail: "Results published as SARIF in the repository." },
        ],
      },
      {
        id: "release",
        title: "Release",
        lead: "A version tag triggers publication, only if continuous integration is green on that commit.",
        gates: [
          { name: "Guard", detail: "No release without successful CI on the same commit." },
          { name: "Docker Bake", detail: "The three images built together, with cache." },
          { name: "SBOM and provenance", detail: "BuildKit attestations attached to every image." },
          {
            name: "cosign signing",
            detail: "Keyless signature, bound to the pipeline's OIDC identity.",
          },
          { name: "Helm values", detail: "Digests published for Kubernetes deployments." },
          {
            name: "Promotion",
            detail: "A dedicated pipeline verifies signatures before promoting a release.",
          },
        ],
      },
      {
        id: "deploy",
        title: "Deployment",
        lead: "A release is deployed, to a protected environment, after verification.",
        gates: [
          {
            name: "Protected environment",
            detail: "Production deploys go through a dedicated GitHub environment.",
          },
          {
            name: "Signature verification",
            detail: "The three images are verified before anything happens.",
          },
          {
            name: "Private network",
            detail:
              "The pipeline joins the admin network through identity federation, no stored key.",
          },
          {
            name: "Waited start",
            detail: "Docker Compose waits until every service is healthy, ten minutes at most.",
          },
          {
            name: "Public check",
            detail: "The pipeline checks the application answers from the internet.",
          },
          { name: "Rollback", detail: "Redeploying the previous release is the same command." },
        ],
      },
    ],
    practices: {
      title: "Day to day",
      items: [
        {
          title: "Typed everywhere",
          body: "Strict Python and TypeScript; the interface derives its types from the API.",
        },
        {
          title: "Tracked dependencies",
          body: "Dependabot on npm, Python, Docker, Compose and actions; everything pinned.",
        },
        {
          title: "Checked documentation",
          body: "Guides, commands and links checked on every change.",
        },
        {
          title: "Written decisions",
          body: "Architecture choices have their record, with context and alternatives.",
        },
        {
          title: "Full local environment",
          body: "The whole platform starts in one command, observability included.",
        },
        {
          title: "Design system",
          body: "Tokens, components and interface rules documented and applied everywhere.",
        },
      ],
    },
  },

  solutions: {
    banks: {
      meta: {
        title: "Banking: KYC, lending and document compliance",
        description:
          "Repody reads bank statements, proof of income and file documents, checks their consistency and flags what needs review, on the bank's own infrastructure.",
      },
      hero: {
        title: "Banking files checked in minutes",
        lead: "Account opening, lending, compliance: the same documents come back every day. Repody extracts their data, checks their consistency and lets your teams focus on the cases that deserve it.",
      },
      docs: [
        "Bank statements",
        "Payslips and income certificates",
        "Bank details (RIB)",
        "Tax notices",
        "Invoices and pro forma",
        "Articles and company registrations",
      ],
      cases: [
        {
          title: "Account opening",
          body: "Holder, IBAN, period and balances of a statement, compared with the opening form.",
        },
        {
          title: "Loan underwriting",
          body: "Declared income, payslips and statements reconciled; a gap is flagged before committee.",
        },
        {
          title: "Compliance checks",
          body: "Missing documents, expired dates, inconsistent amounts: every file goes through the same rules.",
        },
      ],
      rules: [
        "The statement is less than three months old",
        "The statement holder matches the customer",
        "The payslip salary matches the statement transfers",
        "The IBAN is present and valid",
      ],
      posture:
        "Banking data stays in the bank's information system: Repody installs on your servers, behind your identity provider.",
    },
    insurance: {
      meta: {
        title: "Insurance: claims and underwriting",
        description:
          "Repody reads accident reports, quotes, invoices and expert reports, cross-checks the documents of a claim file and flags inconsistencies, on the insurer's own infrastructure.",
      },
      hero: {
        title: "Consistent claim files before they are paid",
        lead: "A claim file brings together several documents that must tell the same story. Repody reads them all and checks that they agree.",
      },
      docs: [
        "Accident reports",
        "Garage quotes and invoices",
        "Expert reports",
        "Insurance certificates",
        "Vehicle registrations",
        "Medical invoices",
      ],
      cases: [
        {
          title: "Claims handling",
          body: "The vehicle on the report is the one on the invoice, dates follow each other, amounts are consistent.",
        },
        {
          title: "Underwriting",
          body: "Data from attached documents feeds the file without retyping.",
        },
        {
          title: "Fraud prevention",
          body: "Gaps between documents are flagged systematically, not by the luck of a re-read.",
        },
      ],
      rules: [
        "Same registration on the report and the invoice",
        "The invoice is dated after the accident",
        "The invoice amount does not exceed the quote",
        "The certificate covers the accident date",
      ],
      posture:
        "Policyholders' files stay with the insurer: Repody installs on your servers, with your roles and identity provider.",
    },
    telecom: {
      meta: {
        title: "Telecom: contracts, purchasing and supporting documents",
        description:
          "Repody reads subscription contracts, purchase orders and supplier invoices, checks signatures, amounts and company identifiers, on the operator's own infrastructure.",
      },
      hero: {
        title: "Contracts and purchases checked at scale",
        lead: "Business subscriptions, purchasing, regulatory files: high volumes and very varied documents. Repody processes them at the pace of your flows.",
      },
      docs: [
        "Subscription contracts",
        "Purchase orders",
        "Supplier invoices",
        "Company documents",
        "Delivery notes",
        "Certificates",
      ],
      cases: [
        {
          title: "Business subscriptions",
          body: "Company name, ICE, plan and monthly fee extracted from the contract; an unsigned contract is rejected.",
        },
        {
          title: "Accounts payable",
          body: "Invoice, purchase order and delivery reconciled before payment.",
        },
        {
          title: "Regulatory files",
          body: "Complete, up-to-date documents, checked against the same rules every time.",
        },
      ],
      rules: [
        "The contract is signed",
        "The ICE is present",
        "The invoice total equals the purchase order's",
        "The sum of lines equals the net total",
      ],
      posture:
        "Subscriber and supplier data stays with the operator: Repody installs on your servers.",
    },
    labels: {
      docs: "Documents handled",
      cases: "Use cases",
      rules: "Example rules",
      posture: "Your data",
    },
  },

  contact: {
    meta: {
      title: "Request a demo",
      description: "A 30-minute demo, then a pilot on your own documents and rules.",
    },
    title: "Let's see Repody on your documents",
    lead: "Tell us which documents you handle and what you want to check. We get back to you within two business days.",
    form: {
      name: "Name",
      email: "Work email",
      company: "Company",
      sector: "Industry",
      sectors: ["Banking", "Insurance", "Telecom", "Other"],
      message: "Your documents and needs",
      placeholder:
        "For example: 3,000 bank statements a month for account opening, checking the holder and the period.",
      submit: "Send the request",
      note: "The button opens your email app with the request ready to send.",
      subject: "Repody demo request",
    },
    next: {
      title: "What happens next",
      items: [
        "A 30-minute call to understand your documents and rules",
        "A demo on documents close to yours",
        "A pilot on your files, in your environment or an isolated one",
        "A licence and support proposal",
      ],
    },
    direct: "Or write to us directly:",
  },

  legal: {
    meta: { title: "Legal notice", description: "Legal notice for repody.com." },
    title: "Legal notice",
    body: [
      "The repody.com website presents the Repody platform.",
      "For any question about the site, write to the address on the contact page.",
      "Names and trademarks mentioned belong to their respective owners.",
    ],
  },
  privacy: {
    meta: { title: "Privacy", description: "How repody.com handles your data." },
    title: "Privacy",
    body: [
      "This site sets no tracking cookies and uses no third-party analytics.",
      "The contact form sends nothing by itself: it prepares an email in your mail app, which you choose to send.",
      "The data you send us is only used to answer you and is never shared.",
      "Under Law 09-08, you can ask to access, correct or delete your data at the contact address.",
    ],
  },
};
