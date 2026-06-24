#!/usr/bin/env node
/**
 * Render values-local-registry.yaml for each local Helm chart from pinned-images.env.
 */
import { writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { renderLocalRegistryValuesYaml } from "./local-registry-values.mjs";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");

const targets = [
  ["deploy/helm/repody-data/values-local-registry.yaml", "data"],
  ["deploy/helm/repody-queue/values-local-registry.yaml", "queue"],
  ["deploy/helm/repody-auth/values-local-registry.yaml", "auth"],
  ["deploy/helm/repody/values-local-registry.yaml", "app"],
];

for (const [rel, chart] of targets) {
  const out = path.join(root, rel);
  writeFileSync(out, renderLocalRegistryValuesYaml(root, chart), "utf8");
  console.error(`ok: ${rel}`);
}
