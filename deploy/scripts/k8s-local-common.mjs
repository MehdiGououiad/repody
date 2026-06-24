import { readFileSync } from "node:fs";
import path from "node:path";

export const LOCAL_HOSTS = Object.freeze({
  web: "app.repody.local",
  api: "api.repody.local",
  files: "files.repody.local",
  auth: "auth.repody.local",
  argocd: "argocd.repody.local",
  grafana: "grafana.repody.local",
  bugsink: "bugsink.repody.local",
  harbor: "harbor.repody.local",
});

export const LOCAL_HOST_LIST = Object.freeze(Object.values(LOCAL_HOSTS));

export const LOCAL_ADDONS = Object.freeze([
  "grafana",
  "loki",
  "promtail",
  "tempo",
  "bugsink",
]);

export const LOCAL_CREDENTIALS = Object.freeze({
  keycloakUser: "operator@repody.local",
  keycloakPassword: "repody-dev",
  keycloakClientId: "repody-web",
  keycloakClientSecret: "repody-web-dev-secret",
  grafanaUser: "admin",
  grafanaPassword: "audit",
  bugsinkUser: "admin@example.com",
  bugsinkPassword: "admin",
});

export const LOCAL_HOSTS_LINE = `127.0.0.1 ${LOCAL_HOST_LIST.join(" ")}`;

export function localUrl(host, pathName = "") {
  return `http://${host}${pathName}`;
}

export function readPinnedImages(root) {
  const file = path.join(root, "deploy/pinned-images.env");
  const parsed = {};
  for (const raw of readFileSync(file, "utf8").split(/\r?\n/)) {
    const line = raw.trim();
    if (!line || line.startsWith("#")) continue;
    const index = line.indexOf("=");
    if (index <= 0) continue;
    parsed[line.slice(0, index)] = line.slice(index + 1);
  }
  return parsed;
}

export function requirePinnedImage(pinned, key) {
  const value = pinned[key];
  if (!value) {
    throw new Error(`Missing ${key} in deploy/pinned-images.env`);
  }
  return value;
}
