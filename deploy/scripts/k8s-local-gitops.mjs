/**
 * GitOps handoff helpers: Argo CD owns steady state; Helm CLI is bootstrap-only.
 */
import { waitFor } from "./k8s-local-process.mjs";

export const LOCAL_ARGO_APP_NAMES = [
  "repody-local-data",
  "repody-local-queue",
  "repody-local-auth",
  "repody-local-app",
];

/** @type {{ namespace: string; release: string }[]} */
export const GITOPS_HELM_HANDOFF = [
  { namespace: "repody-data", release: "repody-data" },
  { namespace: "repody-queue", release: "repody-queue" },
  { namespace: "repody-auth", release: "repody-auth" },
  { namespace: "repody-app", release: "repody" },
];

/**
 * @param {{
 *   captureOptional: (cmd: string, args: string[]) => string | null;
 *   run: (cmd: string, args: string[]) => void;
 *   argoNamespace?: string;
 * }} deps
 */
export function createGitOpsHandoffCommands({
  captureOptional,
  run,
  argoNamespace = "argocd",
}) {
  /** @param {string} namespace @param {string} releaseName */
  function releaseHelmOwnership(namespace, releaseName) {
    const names = captureOptional("kubectl", [
      "-n",
      namespace,
      "get",
      "secrets",
      "-l",
      `owner=helm,name=${releaseName}`,
      "-o",
      "jsonpath={.items[*].metadata.name}",
    ]);
    if (!names) return 0;
    let removed = 0;
    for (const name of names.split(/\s+/).filter(Boolean)) {
      run("kubectl", [
        "-n",
        namespace,
        "delete",
        "secret",
        name,
        "--ignore-not-found",
        "--wait=false",
      ]);
      removed += 1;
    }
    return removed;
  }

  function handoffHelmReleasesToArgo() {
    let total = 0;
    for (const { namespace, release } of GITOPS_HELM_HANDOFF) {
      const count = releaseHelmOwnership(namespace, release);
      if (count > 0) {
        console.error(
          `ok: released Helm release metadata ${namespace}/${release} (${count} revision secret(s))`,
        );
        total += count;
      }
    }
    if (total === 0) {
      console.error("ok: no Helm release secrets — Argo CD already owns workloads");
    }
    return total;
  }

  function refreshArgoApplications(appNames = LOCAL_ARGO_APP_NAMES) {
    for (const app of appNames) {
      captureOptional("kubectl", [
        "-n",
        argoNamespace,
        "annotate",
        `application/${app}`,
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
          `application/${appName}`,
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
      `Argo CD ${appName} Synced`,
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
    handoffHelmReleasesToArgo,
    refreshArgoApplications,
    releaseHelmOwnership,
    waitForArgoApplicationsSynced,
    waitForArgoAppSynced,
  };
}
