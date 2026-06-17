/**
 * Air-gap release manifest — image and model lists for regulated / restricted-egress deploys.
 * @see docs/AIRGAP.md
 */
import { readFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import {
  REPODY_VLM_DEFAULT_TARGET,
  REPODY_VLM_PULL_SOURCE,
} from "../repody-vlm-model.constants.mjs";

const root = join(dirname(fileURLToPath(import.meta.url)), "../..");

/** v1 bundle: core platform + logs + error tracking (no traces / GPU). */
export const AIRGAP_V1_MODULES = [
  "infra",
  "control",
  "workers",
  "edge",
  "obs",
  "bugsink",
];

/** @returns {Record<string, string>} */
export function loadPinnedImages() {
  const path = join(root, "deploy/pinned-images.env");
  /** @type {Record<string, string>} */
  const env = {};
  for (const line of readFileSync(path, "utf8").replace(/^\uFEFF/, "").split(/\r?\n/)) {
    if (!line || line.startsWith("#")) continue;
    const idx = line.indexOf("=");
    if (idx < 1) continue;
    env[line.slice(0, idx).trim()] = line.slice(idx + 1).trim();
  }
  return env;
}

/**
 * @param {{ tag?: string; registry?: string }} [options]
 */
export function airgapAppImages(options = {}) {
  const tag = options.tag ?? "latest";
  const prefix = options.registry?.replace(/\/$/, "");
  const base = prefix ? `${prefix}/` : "";
  return [
    `${base}repody-api:${tag}`,
    `${base}repody-worker:${tag}`,
    `${base}repody-web:${tag}`,
  ];
}

/**
 * Third-party images for Compose prod + obs + bugsink (deduped).
 * @param {Record<string, string>} [pinned]
 */
export function airgapUpstreamImages(pinned = loadPinnedImages()) {
  const postgres =
    pinned.REPODY_POSTGRES_IMAGE ?? pinned.REPODY_HATCHET_POSTGRES_IMAGE ?? "postgres:17.10-alpine";
  return [
    ...new Set([
      postgres,
      pinned.REPODY_REDIS_IMAGE ?? "redis:8.8.0-alpine",
      pinned.REPODY_MINIO_IMAGE ?? "pgsty/minio:RELEASE.2026-04-17T00-00-00Z",
      pinned.REPODY_HATCHET_LITE_IMAGE ?? "ghcr.io/hatchet-dev/hatchet/hatchet-lite:latest",
      pinned.REPODY_HATCHET_ADMIN_IMAGE ?? "ghcr.io/hatchet-dev/hatchet/hatchet-admin:latest",
      pinned.REPODY_LOKI_IMAGE ?? "grafana/loki:3.6.11",
      pinned.REPODY_PROMTAIL_IMAGE ?? "grafana/promtail:3.6.11",
      pinned.REPODY_GRAFANA_IMAGE ?? "grafana/grafana:12.4.1",
      pinned.REPODY_BUGSINK_IMAGE ?? "bugsink/bugsink:2",
      pinned.REPODY_BUSYBOX_IMAGE ?? "busybox:1.37.0",
      pinned.REPODY_KUBECTL_IMAGE ?? "bitnami/kubectl:1.34.2",
    ]),
  ];
}

/** @param {{ tag?: string; registry?: string }} [options] */
export function airgapImageManifest(options = {}) {
  const upstream = airgapUpstreamImages();
  const app = airgapAppImages(options);
  return {
    version: "1",
    modules: AIRGAP_V1_MODULES,
    tag: options.tag ?? "latest",
    registry: options.registry ?? "",
    upstream,
    app,
    all: [...new Set([...upstream, ...airgapAppImages({ tag: options.tag ?? "latest" })])],
  };
}

export const AIRGAP_MODEL = {
  type: "docker-model-runner",
  target: REPODY_VLM_DEFAULT_TARGET,
  pullSource: REPODY_VLM_PULL_SOURCE,
  bundleFile: "models/repody-vlm-model.tar",
};

/**
 * Safe filename for an image reference (e.g. `postgres-17.6-alpine.tar`).
 * @param {string} imageRef
 */
export function imageArchiveName(imageRef) {
  return `${imageRef.replace(/[/:@]/g, "-")}.tar`;
}
