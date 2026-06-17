/**
 * Modular platform composition — single source of truth for deploy units.
 *
 * @see docs/PLATFORM.md
 * @see deploy/ENV.md
 */
import { COMPOSE } from "./compose-paths.mjs";

/** @typedef {"infra" | "control" | "workers" | "edge" | "obs" | "traces" | "bugsink" | "auth"} ModuleId */

/** @typedef {{
 *   warmup?: boolean;
 *   lan?: boolean;
 *   public?: boolean;
 *   scale?: boolean;
 * }} StackOverlays */

/** @typedef {{
 *   id: ModuleId;
 *   label: string;
 *   description: string;
 *   services: string[];
 *   files?: string[];
 *   profiles?: string[];
 *   requires?: ModuleId[];
 *   scalable?: boolean;
 *   overlayOnly?: boolean;
 * }} PlatformModule */

/** @typedef {{
 *   id: string;
 *   label: string;
 *   files: string[];
 *   defaultModules: ModuleId[];
 * }} StackPreset */

export const HATCHET_INIT_PROFILE = "init";

/** @type {Record<ModuleId, PlatformModule>} */
export const MODULES = {
  infra: {
    id: "infra",
    label: "Infrastructure",
    description: "Postgres, Redis, MinIO, Hatchet (data + queue plane)",
    services: ["postgres", "redis", "minio", "hatchet-postgres", "hatchet-lite"],
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
    profiles: ["web"],
  },
  obs: {
    id: "obs",
    label: "Observability (logs)",
    description: "Grafana + Loki + Promtail",
    services: ["loki", "grafana", "promtail"],
    files: [COMPOSE.observability],
    profiles: ["obs"],
  },
  traces: {
    id: "traces",
    label: "Observability (traces)",
    description: "Tempo + OTEL on api/workers",
    services: ["tempo"],
    files: [COMPOSE.observabilityTraces],
    profiles: ["obs-traces"],
    requires: ["obs"],
  },
  bugsink: {
    id: "bugsink",
    label: "Bugsink (errors)",
    description: "Self-hosted Sentry-compatible error tracking UI",
    services: ["bugsink-db", "bugsink"],
    files: [COMPOSE.bugsink],
    profiles: ["bugsink"],
  },
  auth: {
    id: "auth",
    label: "Auth (Keycloak)",
    description: "OIDC identity provider for UI users and JWT validation on API",
    services: ["keycloak"],
    files: [COMPOSE.keycloak],
    profiles: ["auth"],
  },
};

/** @type {Record<string, StackPreset>} */
export const STACKS = {
  dev: {
    id: "dev",
    label: "Development",
    files: [COMPOSE.base, COMPOSE.cpu, COMPOSE.dev],
    defaultModules: ["infra", "control", "workers"],
  },
  prod: {
    id: "prod",
    label: "Production (local / single host)",
    files: [COMPOSE.base, COMPOSE.cpu, COMPOSE.prod],
    defaultModules: ["infra", "control", "workers", "edge"],
  },
  "prod-micro": {
    id: "prod-micro",
    label: "Production (separate image tags per role)",
    files: [COMPOSE.base, COMPOSE.cpu, COMPOSE.prod, COMPOSE.microservices],
    defaultModules: ["infra", "control", "workers", "edge"],
  },
  vps: {
    id: "vps",
    label: "Ubuntu VPS (HTTPS + cloud tuning)",
    files: [
      COMPOSE.base,
      COMPOSE.cpu,
      COMPOSE.prod,
      COMPOSE.public,
      COMPOSE.cloud,
      COMPOSE.vps,
    ],
    defaultModules: ["infra", "control", "workers", "edge"],
  },
  gpu: {
    id: "gpu",
    label: "Production + GPU vLLM",
    files: [COMPOSE.base, COMPOSE.cpu, COMPOSE.gpu, COMPOSE.prod],
    defaultModules: ["infra", "control", "workers", "edge"],
  },
  e2e: {
    id: "e2e",
    label: "CI / Playwright smoke",
    files: [COMPOSE.base, COMPOSE.e2e],
    defaultModules: ["infra", "control", "workers", "edge"],
  },
  k8s: {
    id: "k8s",
    label: "Kubernetes (Helm — not Compose)",
    files: [],
    defaultModules: [],
  },
};

const MODULE_ORDER = /** @type {ModuleId[]} */ ([
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
  "hatchet-lite",
  "hatchet-postgres",
];

export const PROD_STACK_IDS = new Set(["prod", "prod-micro", "vps", "gpu"]);

/**
 * @param {string | undefined} stackId
 * @param {StackOverlays} cliOverlays
 */
export function resolveStackRequest(stackId, cliOverlays = {}) {
  const id = stackId ?? "dev";
  if (!STACKS[id]) {
    throw new Error(
      `Unknown stack "${stackId}". Available: ${Object.keys(STACKS).join(", ")}`
    );
  }
  return { stackId: id, overlays: { ...cliOverlays }, extraModules: [] };
}

export function resolveStack(stackId) {
  const { stackId: id } = resolveStackRequest(stackId);
  const stack = STACKS[id];
  if (!stack) {
    throw new Error(
      `Unknown stack "${stackId}". Available: ${Object.keys(STACKS).join(", ")}`
    );
  }
  return stack;
}

/**
 * @param {string[]} filePaths
 * @param {string} stackId
 * @param {StackOverlays} overlays
 */
export function applyStackOverlays(filePaths, stackId, overlays) {
  const paths = [...filePaths];

  if (overlays.warmup && !paths.includes(COMPOSE.warmup)) {
    paths.push(COMPOSE.warmup);
  }

  if (overlays.lan && !paths.includes(COMPOSE.lan)) paths.push(COMPOSE.lan);
  if (overlays.public && !paths.includes(COMPOSE.public)) {
    paths.push(COMPOSE.public);
  }
  if (overlays.scale && !paths.includes(COMPOSE.scale)) {
    paths.push(COMPOSE.scale);
  }

  return paths;
}

export function stackFileArgs(stackId, overlays = {}) {
  return buildPlatformSpec({ stack: stackId, overlays }).fileArgs;
}

export function stackFiles(stackId, overlays = {}) {
  return [...buildPlatformSpec({ stack: stackId, overlays }).filePaths];
}

export function normalizeModules(moduleIds) {
  const set = new Set(moduleIds);
  for (const id of [...set]) {
    for (const req of MODULES[id].requires ?? []) {
      set.add(req);
    }
  }
  return MODULE_ORDER.filter((id) => set.has(id));
}

export function composeFileArgs(paths) {
  const unique = [...new Set(paths)];
  return unique.flatMap((path) => ["-f", path]);
}

export function buildPlatformSpec(options = {}) {
  const { stackId, overlays, extraModules } = resolveStackRequest(
    options.stack,
    options.overlays ?? {}
  );
  const preset = STACKS[stackId];
  if (!preset) {
    throw new Error(
      `Unknown stack "${options.stack}". Run: pnpm compose stacks`
    );
  }

  const withModules = [
    ...(extraModules ?? []),
    ...(options.withModules ?? []),
  ];
  const modules = normalizeModules(
    options.modulesOnly
      ? withModules
      : [...preset.defaultModules, ...withModules]
  );

  const filePaths = options.modulesOnly
    ? []
    : applyStackOverlays(preset.files, stackId, overlays);
  const profiles = [HATCHET_INIT_PROFILE];
  const services = [];

  for (const id of modules) {
    const mod = MODULES[id];
    for (const file of mod.files ?? []) {
      if (options.modulesOnly && mod.overlayOnly) continue;
      if (!filePaths.includes(file)) filePaths.push(file);
    }
    for (const profile of mod.profiles ?? []) {
      if (!profiles.includes(profile)) profiles.push(profile);
    }
    services.push(...mod.services);
  }

  return {
    stack: stackId,
    overlays,
    modules,
    filePaths,
    fileArgs: composeFileArgs(filePaths),
    profiles,
    services: [...new Set(services)],
  };
}

export function parseModuleCsv(csv) {
  if (!csv?.trim()) return [];
  return csv
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean)
    .map((id) => {
      if (!(id in MODULES)) {
        throw new Error(`Unknown module "${id}". Run: pnpm compose modules`);
      }
      return /** @type {ModuleId} */ (id);
    });
}

export function parseOverlayFlags(flags) {
  /** @type {StackOverlays} */
  const overlays = {};
  if (flags.warmup) overlays.warmup = true;
  if (flags.lan) overlays.lan = true;
  if (flags.public) overlays.public = true;
  if (flags.scale) overlays.scale = true;
  return overlays;
}

export function scaleArgs(scale) {
  /** @type {string[]} */
  const args = [];
  if (scale.worker != null && scale.worker > 0) {
    args.push("--scale", `worker=${scale.worker}`);
  }
  if (scale.workerFast != null && scale.workerFast > 0) {
    args.push("--scale", `worker-fast=${scale.workerFast}`);
  }
  return args;
}
