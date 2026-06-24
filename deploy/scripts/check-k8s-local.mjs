#!/usr/bin/env node
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import {
  LOCAL_HOST_LIST,
  readPinnedImages,
} from "./k8s-local-common.mjs";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const pinned = readPinnedImages(root);
const pinnedImages = new Set(Object.values(pinned));

function readAddonManifest(relativePath) {
  return readFileSync(path.join(root, relativePath), "utf8");
}

const obsAddons = readAddonManifest("deploy/k8s/local-addons-obs.yaml");
const gitopsAddons = readAddonManifest("deploy/k8s/local-addons-gitops.yaml");

for (const [label, content] of [
  ["local-addons-obs.yaml", obsAddons],
  ["local-addons-gitops.yaml", gitopsAddons],
]) {
  const images = [...content.matchAll(/^\s*image:\s*"?([^"\s]+)"?\s*$/gm)].map(
    (match) => match[1],
  );
  const unpinnedImages = images.filter((image) => !pinnedImages.has(image));
  if (unpinnedImages.length) {
    throw new Error(
      `deploy/k8s/${label} uses images not present in deploy/pinned-images.env: ${[
        ...new Set(unpinnedImages),
      ].join(", ")}`,
    );
  }

  const hostnames = [
    ...content.matchAll(/^\s*-\s*([a-z0-9.-]+\.repody\.local)\s*$/gm),
  ].map((match) => match[1]);
  const unknownHosts = hostnames.filter((host) => !LOCAL_HOST_LIST.includes(host));
  if (unknownHosts.length) {
    throw new Error(
      `deploy/k8s/${label} uses hosts not present in k8s-local-common.mjs: ${[
        ...new Set(unknownHosts),
      ].join(", ")}`,
    );
  }
}

console.error("local k8s checks passed (addon manifests validated)");
