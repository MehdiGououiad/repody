/**
 * Modular platform composition — single source of truth for deploy units.
 *
 * @see docs/PLATFORM.md
 * @see docs/adr/003-modular-platform-modules.md
 */

/** @typedef {"infra" | "control" | "workers" | "edge" | "obs" | "traces" | "errors"} ModuleId */

/** @typedef {{
 *   id: ModuleId;
 *   label: string;
 *   description: string;
 *   services: string[];
 *   files?: string[];
 *   profiles?: string[];
 *   requires?: ModuleId[];
 *   scalable?: boolean;
 * }} PlatformModule */

/** @typedef {{
 *   id: string;
 *   label: string;
 *   files: string[];
 *   defaultModules: ModuleId[];
 * }} StackPreset */

/** @type {Record<ModuleId, PlatformModule>} */
export const MODULES = {
  infra: {
    id: "infra",
    label: "Infrastructure",
    description: "Postgres, Redis, MinIO, Hatchet (data + queue plane)",
    services: [
      "postgres",
      "redis",
      "minio",
      "hatchet-postgres",
      "hatchet-lite",
      "hatchet-init",
    ],
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
    files: ["compose.observability.yaml"],
    profiles: ["obs"],
  },
  traces: {
    id: "traces",
    label: "Observability (traces)",
    description: "Tempo + OTEL on api/workers",
    services: ["tempo"],
    files: ["compose.observability-traces.yaml"],
    profiles: ["obs-traces"],
    requires: ["obs"],
  },
  errors: {
    id: "errors",
    label: "Error tracking",
    description: "GlitchTip (Sentry-compatible)",
    services: ["glitchtip", "glitchtip-postgres", "glitchtip-valkey"],
    files: ["compose.glitchtip.yaml"],
    profiles: ["glitchtip"],
  },
};

/** @type {Record<string, StackPreset>} */
export const STACKS = {
  dev: {
    id: "dev",
    label: "Development (fast boot)",
    files: [
      "compose.yaml",
      "compose.cpu.yaml",
      "compose.dev.yaml",
      "compose.sentry.yaml",
    ],
    defaultModules: ["infra", "control", "workers"],
  },
  "dev-warm": {
    id: "dev-warm",
    label: "Development (Repody VLM warmup)",
    files: [
      "compose.yaml",
      "compose.cpu.yaml",
      "compose.warmup.yaml",
      "compose.sentry.yaml",
    ],
    defaultModules: ["infra", "control", "workers"],
  },
  prod: {
    id: "prod",
    label: "Production",
    files: [
      "compose.yaml",
      "compose.cpu.yaml",
      "compose.prod.yaml",
      "compose.microservices.yaml",
      "compose.sentry.yaml",
    ],
    defaultModules: ["infra", "control", "workers", "edge"],
  },
  "prod-scale": {
    id: "prod-scale",
    label: "Production (horizontal worker scale)",
    files: [
      "compose.yaml",
      "compose.cpu.yaml",
      "compose.prod.yaml",
      "compose.scale.yaml",
      "compose.microservices.yaml",
      "compose.sentry.yaml",
    ],
    defaultModules: ["infra", "control", "workers", "edge"],
  },
  gpu: {
    id: "gpu",
    label: "Production + GPU vLLM",
    files: [
      "compose.yaml",
      "compose.cpu.yaml",
      "compose.gpu.yaml",
      "compose.prod.yaml",
      "compose.microservices.yaml",
      "compose.sentry.yaml",
    ],
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
  "errors",
]);

export const INFRA_SERVICES = ["postgres", "redis", "minio"];
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
  "hatchet-init",
];

/**
 * @param {string | undefined} stackId
 * @returns {StackPreset}
 */
export function resolveStack(stackId) {
  const id = stackId ?? "dev";
  const stack = STACKS[id];
  if (!stack) {
    throw new Error(
      `Unknown stack "${id}". Available: ${Object.keys(STACKS).join(", ")}`
    );
  }
  return stack;
}

/**
 * @param {ModuleId[]} moduleIds
 * @returns {ModuleId[]}
 */
export function normalizeModules(moduleIds) {
  const set = new Set(moduleIds);
  for (const id of [...set]) {
    for (const req of MODULES[id].requires ?? []) {
      set.add(req);
    }
  }
  return MODULE_ORDER.filter((id) => set.has(id));
}

/**
 * @param {string[]} paths
 * @returns {string[]}
 */
export function composeFileArgs(paths) {
  const unique = [...new Set(paths)];
  return unique.flatMap((path) => ["-f", path]);
}

/**
 * @param {object} [options]
 * @param {string} [options.stack]
 * @param {ModuleId[]} [options.withModules]
 * @param {boolean} [options.modulesOnly] - Start only `withModules` (addon stacks)
 */
export function buildPlatformSpec(options = {}) {
  const stackId = options.stack ?? "dev";
  const preset = resolveStack(stackId);
  const withModules = options.withModules ?? [];
  const modules = normalizeModules(
    options.modulesOnly ? withModules : [...preset.defaultModules, ...withModules]
  );

  /** @type {string[]} */
  const filePaths = options.modulesOnly
    ? []
    : [...preset.files];
  /** @type {string[]} */
  const profiles = [];
  /** @type {string[]} */
  const services = [];

  for (const id of modules) {
    const mod = MODULES[id];
    for (const file of mod.files ?? []) {
      if (!filePaths.includes(file)) filePaths.push(file);
    }
    for (const profile of mod.profiles ?? []) {
      if (!profiles.includes(profile)) profiles.push(profile);
    }
    services.push(...mod.services);
  }

  return {
    stack: stackId,
    modules,
    filePaths,
    fileArgs: composeFileArgs(filePaths),
    profiles,
    services: [...new Set(services)],
  };
}

/**
 * @param {string} csv
 * @returns {ModuleId[]}
 */
export function parseModuleCsv(csv) {
  if (!csv?.trim()) return [];
  return csv
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean)
    .map((id) => {
      if (!(id in MODULES)) {
        throw new Error(`Unknown module "${id}". Run: node scripts/platform.mjs modules`);
      }
      return /** @type {ModuleId} */ (id);
    });
}

/**
 * Map legacy AUDIT_DEV_OBS / flags to module ids.
 * @param {{ obs?: boolean; traces?: boolean; glitchtip?: boolean }} flags
 * @returns {ModuleId[]}
 */
export function modulesFromFlags(flags) {
  /** @type {ModuleId[]} */
  const extra = [];
  if (flags.obs || flags.traces) extra.push("obs");
  if (flags.traces) extra.push("traces");
  if (flags.glitchtip) extra.push("errors");
  return extra;
}

/**
 * @param {object} scale
 * @param {number} [scale.worker]
 * @param {number} [scale.workerFast]
 * @returns {string[]}
 */
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
