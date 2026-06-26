/**
 * GitOps helpers for local Argo CD apps.
 */
import { waitFor } from "./k8s-local-process.mjs";

export const LOCAL_ARGO_ROOT_APP = "repody-local-root";

export const LOCAL_ARGO_APP_NAMES = [
  "repody-local-data",
  "repody-local-queue",
  "repody-local-auth",
  "repody-local-app",
];

/**
 * @param {{
 *   captureOptional: (cmd: string, args: string[]) => string | null;
 *   argoNamespace?: string;
 * }} deps
 */
export function createGitOpsCommands({
  captureOptional,
  argoNamespace = "argocd",
}) {
  function refreshArgoApplications(
    appNames = [LOCAL_ARGO_ROOT_APP, ...LOCAL_ARGO_APP_NAMES],
  ) {
    for (const app of appNames) {
      captureOptional("kubectl", [
        "-n",
        argoNamespace,
        "annotate",
        "application/" + app,
        "argocd.argoproj.io/refresh=hard",
        "--overwrite",
      ]);
    }
  }

  /**
   * @param {string} appName
   * @param {number} timeoutMs
   */
  async function waitForArgoAppSynced(appName, timeoutMs) {
    await waitFor(
      () => {
        const phase = captureOptional("kubectl", [
          "-n",
          argoNamespace,
          "get",
          "application/" + appName,
          "-o",
          "jsonpath={.status.sync.status},{.status.health.status}",
        ]);
        if (!phase) return false;
        const [sync, health] = phase.split(",");
        return (
          sync === "Synced" &&
          (health === "Healthy" || health === "Progressing")
        );
      },
      "Argo CD " + appName + " Synced",
      timeoutMs,
    );
  }

  /**
   * @param {number} timeoutMs
   * @param {string[]} [appNames]
   */
  async function waitForArgoApplicationsSynced(
    timeoutMs,
    appNames = LOCAL_ARGO_APP_NAMES,
  ) {
    for (const app of appNames) {
      await waitForArgoAppSynced(app, timeoutMs);
    }
  }

  return {
    refreshArgoApplications,
    waitForArgoApplicationsSynced,
    waitForArgoAppSynced,
  };
}
