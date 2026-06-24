import { existsSync, readFileSync } from "node:fs";
import path from "node:path";

const DEFAULT_SIMPLE_REGISTRY = "localhost:5001";
const DEFAULT_HARBOR_HOST = "harbor.repody.local";
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
 *   mode: "simple" | "harbor",
 *   localRegistry: string,
 *   registryName: string | null,
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
  const mode = (process.env.REPODY_REGISTRY_MODE ?? "simple").toLowerCase();
  if (mode === "harbor") {
    const harborHost = process.env.REPODY_HARBOR_HOST ?? DEFAULT_HARBOR_HOST;
    const harborProject = process.env.REPODY_HARBOR_PROJECT ?? DEFAULT_HARBOR_PROJECT;
    const harborHttpPort = Number(
      process.env.REPODY_HARBOR_HTTP_PORT ?? DEFAULT_HARBOR_HTTP_PORT,
    );
    const localRegistry =
      process.env.REPODY_LOCAL_REGISTRY?.replace(/\/$/, "") ??
      `${harborHost}:${harborHttpPort}/${harborProject}`;
    return {
      mode: "harbor",
      localRegistry,
      registryName: null,
      registryHost: harborHost,
      harborProject,
      harborHttpPort,
      harborAdminPassword:
        process.env.REPODY_HARBOR_ADMIN_PASSWORD ?? "Harbor12345",
      harborInstallDir:
        process.env.REPODY_HARBOR_INSTALL_DIR ??
        path.join(root, "deploy/harbor/.runtime/harbor"),
      kindConfigFile: path.join(root, "deploy/k8s/kind-repody-local-harbor.yaml"),
      hostsEntry: harborHost,
    };
  }
  return {
    mode: "simple",
    localRegistry: process.env.REPODY_LOCAL_REGISTRY ?? DEFAULT_SIMPLE_REGISTRY,
    registryName: process.env.REPODY_KIND_REGISTRY_NAME ?? "kind-registry",
    registryHost: "localhost",
    harborProject: "",
    harborHttpPort: 5001,
    harborAdminPassword: "",
    harborInstallDir: "",
    kindConfigFile: path.join(root, "deploy/k8s/kind-repody-local.yaml"),
    hostsEntry: null,
  };
}
