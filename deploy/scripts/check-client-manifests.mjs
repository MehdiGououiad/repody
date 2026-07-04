#!/usr/bin/env node
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const appPath = "deploy/client/argocd.application.yaml";

function read(relativePath) {
  return readFileSync(path.join(root, relativePath), "utf8");
}

function scalar(doc, key) {
  const match = doc.match(new RegExp(`^${key}:\\s*(.+)$`, "m"));
  return match?.[1]?.trim().replace(/^["']|["']$/g, "") ?? "";
}

function scalarAtIndent(doc, key, spaces) {
  const match = doc.match(new RegExp(`^ {${spaces}}${key}:\\s*(.+)$`, "m"));
  return match?.[1]?.trim().replace(/^["']|["']$/g, "") ?? "";
}

function yamlListEntries(doc) {
  return [...doc.matchAll(/^\s*-\s+(.+)$/gm)].map((match) =>
    match[1].trim().replace(/^["']|["']$/g, ""),
  );
}

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

const doc = read(appPath);

assert(scalar(doc, "apiVersion") === "argoproj.io/v1alpha1", "client Argo app apiVersion must be argoproj.io/v1alpha1");
assert(scalar(doc, "kind") === "Application", "client Argo app kind must be Application");
assert(scalarAtIndent(doc, "name", 2) === "repody", "client Argo app metadata.name must be repody");
assert(scalarAtIndent(doc, "namespace", 2) === "argocd", "client Argo app namespace must be argocd");
assert(scalarAtIndent(doc, "project", 2) === "default", "client Argo app project must be default");
assert(scalarAtIndent(doc, "path", 6) === "deploy/helm/repody", "client Argo app must point at deploy/helm/repody");
assert(scalarAtIndent(doc, "namespace", 4) === "repody", "client Argo app destination namespace must be repody");
assert(doc.includes("repoURL: CHANGE_ME_VENDOR_REPO_URL"), "client Argo app must keep vendor repo placeholder");
assert(doc.includes("repoURL: CHANGE_ME_CLIENT_GITOPS_REPO_URL"), "client Argo app must keep client GitOps repo placeholder");
assert(doc.includes("targetRevision: CHANGE_ME_VENDOR_TAG"), "client Argo app must keep vendor tag placeholder");
assert(doc.includes("targetRevision: CHANGE_ME_CLIENT_GITOPS_BRANCH"), "client Argo app must keep client branch placeholder");
assert(doc.includes("ref: values"), "client Argo app must define the values source ref");
assert(existsSync(path.join(root, "deploy/helm/repody/Chart.yaml")), "client Argo app chart path is missing");

const values = yamlListEntries(doc).filter((entry) => entry.endsWith(".yaml"));
for (const valueFile of ["values-common.yaml", "$values/values.yaml"]) {
  assert(values.includes(valueFile), `client Argo app missing value file ${valueFile}`);
}
assert(existsSync(path.join(root, "deploy/helm/repody/values-common.yaml")), "values-common.yaml is missing");

console.error("Client manifest checks passed");
