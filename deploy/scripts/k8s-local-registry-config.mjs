import { existsSync, readFileSync } from "node:fs";
import path from "node:path";

/** Resolves without admin hosts file (lvh.me → 127.0.0.1). Override via paths.harbor.local.env. */
const DEFAULT_HARBOR_HOST = "harbor.repody.lvh.me";
const DEFAULT_HARBOR_PROJECT = "repody";
const DEFAULT_HARBOR_HTTP_PORT = "8080";

/** @param {string} root */
export function loadHarborEnvFile(root) {
  const envPath = path.join(root, "deploy/harbor/paths.harbor.local.env");
  if (!existsSync(envPath)) return;
  for (const raw of readFileSync(envPath, "utf8").split(/\r?\n/)) {
    const line = raw.trim();
    if (!line || line.startsWith("#")) continue;
    const index = line.indexOf("=");
    if (index <= 0) continue;
    const key = line.slice(0, index).trim();
    const value = line.slice(index + 1).trim();
    if (key && process.env[key] === undefined) {
      process.env[key] = value;
    }
  }
}

/**
 * @param {string} root
 * @returns {{
 *   localRegistry: string,
 *   registryHost: string,
 *   harborProject: string,
 *   harborHttpPort: number,
 *   harborAdminPassword: string,
 *   harborInstallDir: string,
 *   kindConfigFile: string,
 *   hostsEntry: string | null,
 * }}
 */
export function resolveLocalRegistryConfig(root) {
  loadHarborEnvFile(root);
  const harborHost = process.env.REPODY_HARBOR_HOST ?? DEFAULT_HARBOR_HOST;
  const harborProject = process.env.REPODY_HARBOR_PROJECT ?? DEFAULT_HARBOR_PROJECT;
  const harborHttpPort = Number(
    process.env.REPODY_HARBOR_HTTP_PORT ?? DEFAULT_HARBOR_HTTP_PORT,
  );
  const localRegistry =
    process.env.REPODY_LOCAL_REGISTRY?.replace(/\/$/, "") ??
    `${harborHost}:${harborHttpPort}/${harborProject}`;
  return {
    localRegistry,
    registryHost: harborHost,
    harborProject,
    harborHttpPort,
    harborAdminPassword:
      process.env.REPODY_HARBOR_ADMIN_PASSWORD ?? "Harbor12345",
    harborInstallDir:
      process.env.REPODY_HARBOR_INSTALL_DIR ??
      path.join(root, "deploy/harbor/.runtime/harbor"),
    kindConfigFile: path.join(root, "deploy/k8s/kind-repody-local.yaml"),
    hostsEntry: harborHost.endsWith(".repody.local") ? harborHost : null,
  };
}

/** Keep docker pull/push to local Harbor off HTTP proxies (Docker Desktop / corp VPN). */
export function ensureLocalDockerNoProxy(registryHost) {
  const hosts = [
    "localhost",
    "127.0.0.1",
    registryHost,
    "harbor.repody.lvh.me",
    "harbor.repody.local",
  ];
  const existing = process.env.NO_PROXY ?? process.env.no_proxy ?? "";
  const merged = [
    ...new Set(
      [...existing.split(","), ...hosts]
        .map((entry) => entry.trim())
        .filter(Boolean),
    ),
  ].join(",");
  process.env.NO_PROXY = merged;
  process.env.no_proxy = merged;
}
