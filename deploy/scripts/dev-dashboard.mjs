/**
 * Local dev startup dashboard — URLs, credentials, and what each component does.
 */

const REPODY_LOGIN = "operator@repody.local / repody-dev (use localhost in the browser)";

/** @typedef {{ name: string; url?: string; probeUrl?: string; endpoint?: string; role: string; creds?: string; skip?: boolean }} DevServiceRow */

/**
 * @param {{ apiPort: number; observability: boolean; llama: boolean; extractOnly: boolean }} ctx
 * @returns {{ title: string; rows: DevServiceRow[] }[]}
 */
export function buildDevDashboardSections(ctx) {
  const { apiPort, observability, llama, extractOnly } = ctx;
  /** @type {{ title: string; rows: DevServiceRow[] }[]} */
  const sections = [
    {
      title: "Repody app (open in browser)",
      rows: [
        {
          name: "UI",
          url: "http://localhost:3000",
          role: "Next.js dashboard — workflows, document runs, audits, settings",
          creds: REPODY_LOGIN,
        },
        {
          name: "API",
          url: `http://localhost:${apiPort}`,
          probeUrl: `http://localhost:${apiPort}/v1/healthz`,
          role: "FastAPI backend — REST, SSE run progress, presigned uploads",
        },
        {
          name: "API health",
          url: `http://localhost:${apiPort}/v1/healthz`,
          role: "Liveness + cache, queue, and admission flags",
          skip: true,
        },
      ],
    },
    {
      title: "Auth (Keycloak OIDC)",
      rows: [
        {
          name: "Keycloak admin",
          url: "http://localhost:8080",
          role: "Identity provider admin console — realms, clients, users",
          creds: "admin / admin",
        },
        {
          name: "Repody realm",
          url: "http://localhost:8080/realms/repody",
          role: "OIDC issuer for API and UI login",
          creds: REPODY_LOGIN,
        },
      ],
    },
    {
      title: "Data plane (Docker Compose)",
      rows: [
        {
          name: "PostgreSQL",
          endpoint: "localhost:5432",
          role: "Repody app database (audit_workbench)",
          creds: "audit / audit-local-dev",
        },
        {
          name: "Redis",
          endpoint: "localhost:6379",
          role: "Taskiq job broker + document extraction result cache",
        },
        {
          name: "MinIO API",
          url: "http://localhost:9000",
          probeUrl: "http://localhost:9001",
          role: "S3-compatible object storage for uploaded PDFs",
        },
        {
          name: "MinIO console",
          url: "http://localhost:9001",
          role: "Web UI for buckets and objects",
          creds: "minioadmin / minio-local-dev",
        },
      ],
    },
    {
      title: "Workers (Taskiq — Docker)",
      rows: [
        {
          name: "worker-extract",
          role: "Document-model pool — NuExtract VLM OCR + field extraction (PDF runs)",
        },
        {
          name: "worker-fast",
          role: "Logic-only pool — rules and validation without document inference",
          skip: extractOnly,
        },
      ],
    },
    {
      title: "Inference (host process)",
      rows: [
        {
          name: "NuExtract / llama-server",
          url: "http://localhost:8081/v1/models",
          role: "Multimodal VLM (llama.cpp) — workers call via host.docker.internal",
          skip: !llama,
        },
      ],
    },
  ];

  if (observability) {
    sections.push({
      title: "Observability (Docker — logs, traces, errors)",
      rows: [
        {
          name: "Grafana",
          url: "http://localhost:3030",
          role: "Dashboards and Explore — Loki logs linked to Tempo traces",
          creds: "admin / admin (anonymous browse enabled)",
        },
        {
          name: "Loki",
          url: "http://localhost:3100",
          probeUrl: "http://localhost:3100/ready",
          role: "Log store — JSON from workers (Docker) and API (.logs/repody-api.log)",
        },
        {
          name: "Tempo",
          url: "http://localhost:3200",
          probeUrl: "http://localhost:3200/ready",
          role: "Trace store — search by trace_id from API/worker OTLP export",
        },
        {
          name: "OTEL Collector",
          url: "http://localhost:4318/v1/traces",
          role: "OpenTelemetry ingest — API/workers → Tempo; enables trace_id in logs",
        },
        {
          name: "Promtail",
          role: "Agent — tails Docker stdout and host API log file into Loki",
        },
        {
          name: "Bugsink",
          url: "http://localhost:8090",
          role: "Self-hosted error tracking (Sentry SDK) — set BUGSINK_DSN after creating a project",
          creds: "admin@repody.local / repody-dev",
        },
      ],
    });
  }

  sections.push({
    title: "CLI (this repo)",
    rows: [
      { name: "pnpm dev:status", role: "Probe every URL above and list Compose containers" },
      { name: "pnpm dev:stop", role: "Stop API, UI, NuExtract, and full Compose stack" },
      { name: "pnpm dev:restart", role: "Restart NuExtract + worker containers after GPU resets" },
      { name: "pnpm dev:observability", role: "Start or refresh Grafana/Loki/Tempo/Bugsink only" },
      { name: "pnpm db:migrate", role: "Apply Alembic migrations" },
      { name: "pnpm test:api", role: "Backend pytest suite" },
    ],
  });

  return sections.map((section) => ({
    ...section,
    rows: section.rows.filter((row) => !row.skip),
  }));
}

/**
 * @param {{ apiPort: number; observability: boolean; llama: boolean; extractOnly: boolean; appRunning: boolean; probe?: boolean; fetchProbe?: (url: string, ms: number) => Promise<{ ok: boolean }> }} opts
 */
export async function printDevDashboard(opts) {
  const {
    apiPort,
    observability,
    llama,
    extractOnly,
    appRunning,
    probe = false,
    fetchProbe,
  } = opts;

  const sections = buildDevDashboardSections({ apiPort, observability, llama, extractOnly });

  console.log("\n╔══════════════════════════════════════════════════════════════════╗");
  console.log("║  Repody local dev — ready                                        ║");
  console.log("╚══════════════════════════════════════════════════════════════════╝");

  if (!appRunning) {
    console.log("\n  Host app not started — run: pnpm dev:app  or  pnpm dev:all\n");
  }

  for (const section of sections) {
    if (section.rows.length === 0) continue;
    console.log(`\n── ${section.title} ${"─".repeat(Math.max(0, 58 - section.title.length))}`);
    for (const row of section.rows) {
      if (probe && fetchProbe && (row.probeUrl ?? row.url)) {
        const check = await fetchProbe(row.probeUrl ?? row.url, 2500);
        const mark = check.ok ? "ok" : "--";
        console.log(`\n  [${mark}] ${row.name}`);
      } else if (row.url || row.endpoint) {
        console.log(`\n  · ${row.name}`);
      } else {
        console.log(`\n  · ${row.name}`);
      }
      const loc = row.url ?? row.endpoint;
      if (loc) console.log(`    ${loc}`);
      console.log(`    ${row.role}`);
      if (row.creds) console.log(`    login: ${row.creds}`);
    }
  }

  if (observability) {
    console.log("\n── Loki quick queries ─────────────────────────────────────────────");
    console.log('  {compose_service=~"worker.*|repody-api"}');
    console.log("  Tempo → trace → Logs tab (trace_id correlation)");
  }

  console.log("");
}
