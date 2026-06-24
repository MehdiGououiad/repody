import { readFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "../..");

export const AIRGAP_V1_MODULES = ["control", "workers", "edge"];

export function loadPinnedImages() {
  const path = join(root, "deploy/pinned-images.env");
  const env = {};
  for (const line of readFileSync(path, "utf8").replace(/^\uFEFF/, "").split(/\r?\n/)) {
    if (!line || line.startsWith("#")) continue;
    const idx = line.indexOf("=");
    if (idx < 1) continue;
    env[line.slice(0, idx).trim()] = line.slice(idx + 1).trim();
  }
  return env;
}

export function airgapAppImages(options = {}) {
  const tag = options.tag ?? "latest";
  const prefix = options.registry?.replace(/\/$/, "");
  const base = prefix ? `${prefix}/` : "";
  return [`${base}repody-backend:${tag}`, `${base}repody-web:${tag}`];
}

export function airgapUpstreamImages(pinned = loadPinnedImages(), options = {}) {
  if (!options.includeBundledInfrastructure) return [];
  const postgres =
    pinned.REPODY_POSTGRES_IMAGE ?? pinned.REPODY_HATCHET_POSTGRES_IMAGE ?? "postgres:17.10-alpine";
  return [
    ...new Set([
      postgres,
      pinned.REPODY_REDIS_IMAGE ?? "redis:8.8.0-alpine",
      pinned.REPODY_MINIO_IMAGE ?? "pgsty/minio:RELEASE.2026-04-17T00-00-00Z",
      pinned.REPODY_HATCHET_API_IMAGE ?? "ghcr.io/hatchet-dev/hatchet/hatchet-api:v0.84.0",
      pinned.REPODY_HATCHET_ENGINE_IMAGE ?? "ghcr.io/hatchet-dev/hatchet/hatchet-engine:v0.84.0",
      pinned.REPODY_HATCHET_FRONTEND_IMAGE ?? "ghcr.io/hatchet-dev/hatchet/hatchet-frontend:v0.84.0",
      pinned.REPODY_HATCHET_MIGRATE_IMAGE ?? "ghcr.io/hatchet-dev/hatchet/hatchet-migrate:v0.84.0",
      pinned.REPODY_HATCHET_ADMIN_IMAGE ?? "ghcr.io/hatchet-dev/hatchet/hatchet-admin:v0.84.0",
      pinned.REPODY_BITNAMI_POSTGRES_IMAGE ?? "bitnamilegacy/postgresql:17.6.0-debian-12-r4",
      pinned.REPODY_BITNAMI_RABBITMQ_IMAGE ?? "bitnamilegacy/rabbitmq:4.1.3-debian-12-r1",
      pinned.REPODY_BUSYBOX_IMAGE ?? "busybox:1.37.0",
    ]),
  ];
}

export function airgapImageManifest(options = {}) {
  const upstream = airgapUpstreamImages(loadPinnedImages(), options);
  const app = airgapAppImages(options);
  return {
    version: "1",
    modules: AIRGAP_V1_MODULES,
    tag: options.tag ?? "latest",
    registry: options.registry ?? "",
    upstream,
    app,
    all: [...new Set([...upstream, ...app])],
  };
}

export function imageArchiveName(imageRef) {
  return `${imageRef.replace(/[/:@]/g, "-")}.tar`;
}
