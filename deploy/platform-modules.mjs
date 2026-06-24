/**
 * Platform module catalog — Kubernetes / Helm deployment units.
 *
 * @see docs/PLATFORM.md
 * @see deploy/helm/repody
 */

/** @typedef {"infra" | "control" | "workers" | "edge" | "obs" | "traces" | "bugsink" | "auth"} ModuleId */

/** @typedef {{
 *   id: ModuleId;
 *   label: string;
 *   description: string;
 *   services: string[];
 *   requires?: ModuleId[];
 *   scalable?: boolean;
 * }} PlatformModule */

/** @type {Record<ModuleId, PlatformModule>} */
export const MODULES = {
  infra: {
    id: "infra",
    label: "Infrastructure",
    description: "Postgres, Redis, MinIO, Hatchet (data + queue plane)",
    services: ["postgres", "redis", "minio", "hatchet-stack"],
  },
  control: {
    id: "control",
    label: "Control plane",
    description: "FastAPI — workflows, runs, uploads, dispatch",
    services: ["api"],
  },
  workers: {
    id: "workers",
    label: "Worker plane",
    description: "Hatchet workers (ocr + fast pools); scale horizontally",
    services: ["worker", "worker-fast"],
    scalable: true,
  },
  edge: {
    id: "edge",
    label: "Edge / UI",
    description: "Next.js web (production image)",
    services: ["web"],
  },
  obs: {
    id: "obs",
    label: "Observability (logs)",
    description: "Grafana + Loki + Promtail",
    services: ["loki", "grafana", "promtail"],
  },
  traces: {
    id: "traces",
    label: "Observability (traces)",
    description: "Tempo + OTEL on api/workers",
    services: ["tempo"],
    requires: ["obs"],
  },
  bugsink: {
    id: "bugsink",
    label: "Bugsink (errors)",
    description: "Self-hosted Sentry-compatible error tracking UI",
    services: ["bugsink-db", "bugsink"],
  },
  auth: {
    id: "auth",
    label: "Auth (Keycloak)",
    description: "OIDC identity provider for UI users and JWT validation on API",
    services: ["keycloak"],
  },
};

export const MODULE_ORDER = /** @type {ModuleId[]} */ ([
  "infra",
  "control",
  "workers",
  "edge",
  "obs",
  "traces",
  "bugsink",
  "auth",
]);

export const INFRA_SERVICES = [...MODULES.infra.services];
export const BACKEND_SERVICES = ["api", "worker", "worker-fast"];
export const PLATFORM_LOG_SERVICES = [
  "web",
  "api",
  "worker",
  "worker-fast",
  "postgres",
  "redis",
  "minio",
  "hatchet-stack",
];

export function normalizeModules(moduleIds) {
  const set = new Set(moduleIds);
  for (const id of [...set]) {
    for (const req of MODULES[id].requires ?? []) {
      set.add(req);
    }
  }
  return MODULE_ORDER.filter((id) => set.has(id));
}
