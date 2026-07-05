import { spawnSync } from "node:child_process";
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import path from "node:path";
import { resolveExecutable } from "../runtime-env.mjs";

/**
 * Argo CD — official getting started install (stable manifests).
 * @see https://argo-cd.readthedocs.io/en/stable/getting_started/
 * @see https://argo-cd.readthedocs.io/en/stable/user-guide/sync-options/
 */

export const ARGO_NS = "argocd";
const INSTALL_URL =
  process.env.REPODY_ARGOCD_INSTALL_URL?.trim() ||
  "https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml";

export function createArgocdLab({
  kubectl,
  kubectlOut,
  fail,
  log,
  sleep,
  root,
  runtimeDir,
  state,
  dryRun = false,
}) {
  function vendorRepoUrl() {
    if (process.env.REPODY_VENDOR_REPO_URL?.trim()) return process.env.REPODY_VENDOR_REPO_URL.trim();
    const remote = spawnSync("git", ["config", "--get", "remote.origin.url"], {
      cwd: root,
      encoding: "utf8",
    });
    let url = (remote.stdout ?? "").trim();
    if (url.startsWith("git@github.com:")) {
      url = `https://github.com/${url.slice("git@github.com:".length).replace(/\.git$/, "")}.git`;
    }
    return url || "https://github.com/MehdiGououiad/repody.git";
  }

  function vendorRevision() {
    return process.env.REPODY_VENDOR_REVISION?.trim() || "master";
  }

  function isInstalled() {
    if (state.isFresh("argocd")) return true;
    const ready = kubectlOut([
      "get",
      "deploy",
      "argocd-server",
      "-n",
      ARGO_NS,
      "-o",
      "jsonpath={.status.readyReplicas}",
    ]);
    return ready === "1";
  }

  function isOpenShift() {
    if (dryRun) return false;
    return kubectlOut(["api-resources", "--api-group=config.openshift.io", "-o", "name"]).includes(
      "clusterversions.config.openshift.io",
    );
  }

  /** PSA privileged + OpenShift privileged SCC (lab only). */
  function ensureOpenShiftLab() {
    kubectl(["apply", "-f", path.join(root, "deploy/client/lab/argocd/namespace.yaml")], { dryRun });
    if (!isOpenShift()) return;
    const sccPath = path.join(root, "deploy/client/lab/argocd/openshift-scc.yaml");
    const result = kubectl(["apply", "-f", sccPath], { dryRun });
    if (result.status !== 0) fail(`OpenShift SCC apply failed (${sccPath})`);
    log("argocd", "OpenShift lab: PSA privileged + SCC privileged for argocd service accounts");
  }

  /**
   * Official install (getting started §1):
   * kubectl apply -n argocd --server-side --force-conflicts -f install.yaml
   */
  function install() {
    ensureOpenShiftLab();

    if (isInstalled() && !process.env.REPODY_FORCE_INFRA) {
      log("argocd", `already running in ${ARGO_NS}`);
      state.write({ argocd: { installedAt: state.get("argocd")?.installedAt ?? new Date().toISOString() } });
      return;
    }

    log("argocd", `installing from ${INSTALL_URL}`);
    const result = kubectl(
      ["apply", "-n", ARGO_NS, "--server-side", "--force-conflicts", "-f", INSTALL_URL],
      { dryRun },
    );
    if (result.status !== 0) fail("Argo CD manifest install failed");

    if (!dryRun) {
      // argocd-redis init container creates argocd-redis secret; server depends on redis.
      for (const deploy of ["argocd-redis", "argocd-repo-server", "argocd-server"]) {
        const ok = kubectl(
          ["wait", "--for=condition=Available", `deployment/${deploy}`, "-n", ARGO_NS, "--timeout=600s"],
          { quiet: true },
        );
        if (ok.status !== 0) fail(`Argo CD ${deploy} did not become Available`);
      }
    }

    state.write({ argocd: { installedAt: new Date().toISOString(), installUrl: INSTALL_URL } });
    log("argocd", `installed (${ARGO_NS}) — see getting_started for argocd app sync`);
  }

  function gitLsRemote(url, revision = "HEAD") {
    const ref = revision === "HEAD" ? "HEAD" : revision;
    return spawnSync("git", ["ls-remote", "--heads", url, ref], {
      encoding: "utf8",
      stdio: "pipe",
      shell: false,
      timeout: 30_000,
    });
  }

  function repoAccessibleWithoutAuth(url) {
    const revision = vendorRevision();
    const probe = gitLsRemote(url, revision);
    return probe.status === 0;
  }

  /**
   * Private repos — official repository credentials (getting started / private repos).
   * Public repos skip credentials (anonymous git ls-remote succeeds).
   * @see https://argo-cd.readthedocs.io/en/stable/user-guide/private-repositories/
   */
  function ensureGitRepository() {
    const url = vendorRepoUrl();
    if (repoAccessibleWithoutAuth(url)) {
      log("argocd", `git repository ${url} is reachable without credentials`);
      return;
    }

    const token =
      process.env.REPODY_GITHUB_TOKEN?.trim() ||
      process.env.GITHUB_TOKEN?.trim() ||
      process.env.GH_TOKEN?.trim();
    if (!token) {
      fail(
        `Argo CD cannot clone ${url}. Set REPODY_GITHUB_TOKEN to a GitHub PAT with repo read access, or make the repository public.`,
      );
    }

    mkdirSync(runtimeDir, { recursive: true });
    const secretPath = path.join(runtimeDir, "argocd-repo-secret.yaml");
    const secretYaml = `apiVersion: v1
kind: Secret
metadata:
  name: repody-vendor-git
  namespace: ${ARGO_NS}
  labels:
    argocd.argoproj.io/secret-type: repository
stringData:
  type: git
  url: ${url}
  username: git
  password: ${token}
`;
    writeFileSync(secretPath, secretYaml, "utf8");
    const result = kubectl(["apply", "-f", secretPath], { dryRun });
    if (result.status !== 0) fail("Argo CD repository secret apply failed");
    log("argocd", `git repository credentials registered for ${url}`);
  }

  function applyApplications(profile) {
    const templatePath = path.join(root, "deploy/client/lab/argocd", `applications-${profile}.yaml`);
    let yaml = readFileSync(templatePath, "utf8");
    yaml = yaml
      .replaceAll("VENDOR_REPO_URL", vendorRepoUrl())
      .replaceAll("VENDOR_REVISION", vendorRevision());

    mkdirSync(runtimeDir, { recursive: true });
    const outPath = path.join(runtimeDir, `argocd-applications-${profile}.yaml`);
    writeFileSync(outPath, yaml, "utf8");
    kubectl(["apply", "-f", outPath], { dryRun });
    log("argocd", `Applications registered (${profile}) — run sync to deploy`);
  }

  function appNames(profile) {
    return profile === "external" ? ["repody-auth", "repody"] : ["repody-data", "repody-auth", "repody"];
  }

  function argocdEnv() {
    return {
      ...process.env,
      ARGOCD_OPTS: process.env.ARGOCD_OPTS || "--port-forward-namespace argocd",
    };
  }

  /** Official sync: argocd login --core then argocd app sync (getting started §7). */
  function syncApps(names) {
    const bin = resolveExecutable("argocd");
    const hasCli = spawnSync(bin, ["version", "--client"], { encoding: "utf8", stdio: "pipe" }).status === 0;

    if (hasCli && !dryRun) {
      kubectl(["config", "set-context", "--current", `--namespace=${ARGO_NS}`], { quiet: true });
      const login = spawnSync(bin, ["login", "--core"], {
        encoding: "utf8",
        stdio: "pipe",
        shell: false,
        env: argocdEnv(),
      });
      if (login.status !== 0) {
        fail(`argocd login --core failed: ${(login.stderr ?? login.stdout ?? "").trim()}`);
      }
      for (const name of names) {
        const r = spawnSync(
          bin,
          ["app", "sync", name, "--prune", "--timeout", "900"],
          { encoding: "utf8", stdio: "inherit", shell: false, env: argocdEnv() },
        );
        if (r.status !== 0) fail(`argocd app sync ${name} failed`);
      }
      return;
    }

    for (const name of names) {
      kubectl(
        ["annotate", "application", name, "-n", ARGO_NS, "argocd.argoproj.io/refresh=hard", "--overwrite"],
        { quiet: true },
      );
      kubectl(
        [
          "patch",
          "application",
          name,
          "-n",
          ARGO_NS,
          "--type",
          "merge",
          "-p",
          '{"operation":{"sync":{"revision":"HEAD","prune":true}}}',
        ],
        { quiet: true },
      );
    }
  }

  function waitHealthy(appNames, timeoutSec = 720) {
    if (dryRun) return;
    const deadline = Date.now() + timeoutSec * 1000;
    while (Date.now() < deadline) {
      let allOk = true;
      for (const name of appNames) {
        const health = kubectlOut([
          "get",
          "application",
          name,
          "-n",
          ARGO_NS,
          "-o",
          "jsonpath={.status.health.status}",
        ]);
        const sync = kubectlOut([
          "get",
          "application",
          name,
          "-n",
          ARGO_NS,
          "-o",
          "jsonpath={.status.sync.status}",
        ]);
        if (health !== "Healthy" || sync !== "Synced") {
          allOk = false;
          break;
        }
      }
      if (allOk) {
        log("argocd", "Repody applications Healthy + Synced");
        return;
      }
      sleep(5000);
    }
    fail("Argo CD applications did not become Healthy/Synced in time");
  }

  return {
    install,
    ensureGitRepository,
    applyApplications,
    syncApps,
    waitHealthy,
    appNames,
    ARGO_NS,
    vendorRepoUrl,
    vendorRevision,
    isInstalled,
  };
}
