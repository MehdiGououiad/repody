import { existsSync } from "node:fs";
import path from "node:path";
import { requirePinnedImage } from "./k8s-local-common.mjs";

function splitImageRef(image) {
  const normalized = image
    .replace(/^docker\.io\//, "")
    .replace(/^registry-1\.docker\.io\//, "");
  const tagIdx = normalized.lastIndexOf(":");
  if (tagIdx === -1 || tagIdx < normalized.lastIndexOf("/")) {
    return { repository: normalized, tag: "latest" };
  }
  return {
    repository: normalized.slice(0, tagIdx),
    tag: normalized.slice(tagIdx + 1),
  };
}

/** @param {string} localRegistry @param {string} image */
function harborImageSets(localRegistry, image) {
  const { repository, tag } = splitImageRef(image);
  return {
    repository: `${localRegistry}/${repository}`,
    tag,
  };
}

/** @param {string} localRegistry @param {string} image — bitnami charts prepend global.imageRegistry */
function registryImageSets(image) {
  return splitImageRef(image);
}

export function createLocalHelmCommands({
  capture,
  chartDir,
  hasFlag,
  keycloakImage,
  localRegistry,
  localRegistryRef,
  pinnedImages,
  run,
  truthyEnv,
  valuesBase,
  valuesLocal,
}) {
  /** @param {string[]} extraHelmSets */
  function collectHelmImages(extraHelmSets = []) {
    const args = [
      "template",
      "repody",
      chartDir,
      "-f",
      valuesBase,
      "-f",
      valuesLocal,
      "--set",
      "global.imageRegistry=",
      ...extraHelmSets,
    ];
    const rendered = capture("helm", args);
    const images = new Set();
    for (const line of rendered.split("\n")) {
      const match = line.match(/^\s*image:\s*["']?([^"'\s]+)["']?\s*$/);
      if (match) {
        images.add(
          match[1]
            .replace(/^docker\.io\//, "")
            .replace(/^registry-1\.docker\.io\//, ""),
        );
      }
    }
    return [...images];
  }

  /** @param {{ backendTag: string, webTag: string, omitImageTags?: boolean }} tags */
  function buildRegistryHelmSets({ backendTag, webTag, omitImageTags = false }) {
    const hatchetApi = harborImageSets(
      localRegistry,
      requirePinnedImage(pinnedImages, "REPODY_HATCHET_API_IMAGE"),
    );
    const hatchetMigrate = harborImageSets(
      localRegistry,
      requirePinnedImage(pinnedImages, "REPODY_HATCHET_MIGRATE_IMAGE"),
    );
    const hatchetAdmin = harborImageSets(
      localRegistry,
      requirePinnedImage(pinnedImages, "REPODY_HATCHET_ADMIN_IMAGE"),
    );
    const hatchetEngine = harborImageSets(
      localRegistry,
      requirePinnedImage(pinnedImages, "REPODY_HATCHET_ENGINE_IMAGE"),
    );
    const hatchetFrontend = harborImageSets(
      localRegistry,
      requirePinnedImage(pinnedImages, "REPODY_HATCHET_FRONTEND_IMAGE"),
    );
    const hatchetPostgres = registryImageSets(
      requirePinnedImage(pinnedImages, "REPODY_BITNAMI_POSTGRES_IMAGE"),
    );
    const hatchetPostgresInit = registryImageSets(
      requirePinnedImage(pinnedImages, "REPODY_POSTGRES_IMAGE"),
    );
    const hatchetRabbitmq = registryImageSets(
      requirePinnedImage(pinnedImages, "REPODY_BITNAMI_RABBITMQ_IMAGE"),
    );

    return [
      "--set",
      `global.imageRegistry=${localRegistry}`,
      "--set",
      "global.security.allowInsecureImages=true",
      ...(omitImageTags
        ? []
        : [
            "--set",
            `images.backend.repository=${localRegistry}/repody-backend`,
            "--set",
            `images.backend.tag=${backendTag}`,
            "--set",
            `images.backend.pullPolicy=IfNotPresent`,
            "--set",
            `images.api.repository=${localRegistry}/repody-backend`,
            "--set",
            `images.worker.repository=${localRegistry}/repody-backend`,
            "--set",
            `images.web.repository=${localRegistry}/repody-web`,
            "--set",
            `images.api.tag=${backendTag}`,
            "--set",
            `images.worker.tag=${backendTag}`,
            "--set",
            `images.web.tag=${webTag}`,
            "--set",
            "images.api.pullPolicy=IfNotPresent",
            "--set",
            "images.worker.pullPolicy=IfNotPresent",
            "--set",
            "images.web.pullPolicy=IfNotPresent",
          ]),
      "--set",
      `hatchet.waitInitImage=${localRegistryRef(requirePinnedImage(pinnedImages, "REPODY_BUSYBOX_IMAGE"))}`,
      "--set",
      `hatchet-stack.sharedConfig.image.tag=${hatchetApi.tag}`,
      "--set",
      `hatchet-stack.api.image.repository=${hatchetApi.repository}`,
      "--set",
      `hatchet-stack.api.image.tag=${hatchetApi.tag}`,
      "--set",
      `hatchet-stack.api.migrationJob.image.repository=${hatchetMigrate.repository}`,
      "--set",
      `hatchet-stack.api.migrationJob.image.tag=${hatchetMigrate.tag}`,
      "--set",
      `hatchet-stack.api.setupJob.image.repository=${hatchetAdmin.repository}`,
      "--set",
      `hatchet-stack.api.setupJob.image.tag=${hatchetAdmin.tag}`,
      "--set",
      `hatchet-stack.engine.image.repository=${hatchetEngine.repository}`,
      "--set",
      `hatchet-stack.engine.image.tag=${hatchetEngine.tag}`,
      "--set",
      `hatchet-stack.frontend.image.repository=${hatchetFrontend.repository}`,
      "--set",
      `hatchet-stack.frontend.image.tag=${hatchetFrontend.tag}`,
      "--set",
      `hatchet-stack.postgres.image.repository=${hatchetPostgres.repository}`,
      "--set",
      `hatchet-stack.postgres.image.tag=${hatchetPostgres.tag}`,
      "--set",
      `hatchet-stack.rabbitmq.image.repository=${hatchetRabbitmq.repository}`,
      "--set",
      `hatchet-stack.rabbitmq.image.tag=${hatchetRabbitmq.tag}`,
      "--set",
      `hatchet-stack.api.postgresImage.repository=${hatchetPostgresInit.repository}`,
      "--set",
      `hatchet-stack.api.postgresImage.tag=${hatchetPostgresInit.tag}`,
      "--set",
      `keycloak.image=${localRegistryRef(keycloakImage)}`,
    ];
  }

  function ensureHelmDependencies() {
    const chartLock = path.join(chartDir, "Chart.lock");
    const expectedCharts = [
      "postgresql-18.7.6.tgz",
      "redis-27.0.10.tgz",
      "minio-17.0.21.tgz",
      "hatchet-stack-0.11.0.tgz",
    ].map((name) => path.join(chartDir, "charts", name));
    const refresh = hasFlag("--deps") || truthyEnv("REPODY_K8S_LOCAL_REFRESH_DEPS");
    if (!refresh && existsSync(chartLock) && expectedCharts.every((chart) => existsSync(chart))) {
      console.error("ok: Helm chart dependencies already present");
      return;
    }
    run("node", ["scripts/helm-deps.mjs"]);
  }

  function externalInferenceHelmSets() {
    const sets = [];
    if (process.env.REPODY_VLLM_BASE_URL) {
      sets.push("--set", `config.vllmBaseUrl=${process.env.REPODY_VLLM_BASE_URL}`);
    }
    if (process.env.REPODY_VLLM_SERVED_MODEL) {
      sets.push("--set", `config.vllmServedModel=${process.env.REPODY_VLLM_SERVED_MODEL}`);
    }
    if (process.env.REPODY_VLLM_API_KEY) {
      sets.push("--set", `secrets.vllmApiKey=${process.env.REPODY_VLLM_API_KEY}`);
    }
    return sets;
  }

  return {
    buildRegistryHelmSets,
    collectHelmImages,
    ensureHelmDependencies,
    externalInferenceHelmSets,
  };
}
