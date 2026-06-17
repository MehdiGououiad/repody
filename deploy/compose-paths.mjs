/**
 * Compose file locations — single path helper for stacks, CLI, and bash sync.
 */
export const COMPOSE_DIR = "deploy/compose";

/** @param {string} name Filename under deploy/compose/ (e.g. "base.yaml") */
export function composeFile(name) {
  return `${COMPOSE_DIR}/${name}`;
}

/** @type {Record<string, string>} */
export const COMPOSE = {
  base: composeFile("base.yaml"),
  cpu: composeFile("cpu.yaml"),
  dev: composeFile("dev.yaml"),
  warmup: composeFile("warmup.yaml"),
  prod: composeFile("prod.yaml"),
  scale: composeFile("scale.yaml"),
  gpu: composeFile("gpu.yaml"),
  lan: composeFile("lan.yaml"),
  public: composeFile("public.yaml"),
  cloud: composeFile("cloud.yaml"),
  vps: composeFile("vps.yaml"),
  microservices: composeFile("microservices.yaml"),
  bugsink: composeFile("bugsink.yaml"),
  keycloak: composeFile("keycloak.yaml"),
  observability: composeFile("observability.yaml"),
  observabilityTraces: composeFile("observability-traces.yaml"),
  e2e: composeFile("e2e.yaml"),
};
