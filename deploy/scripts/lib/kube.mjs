import { spawnSync } from "node:child_process";
import { resolveExecutable } from "../runtime-env.mjs";

/**
 * Standard Kubernetes CLI (kubectl). Works on OpenShift without oc.
 * @param {object} opts
 * @param {(message: string, code?: number) => never} opts.fail
 * @param {(ms: number) => void} opts.sleep
 * @param {NodeJS.ProcessEnv} [opts.env]
 */
export function createKubeCli({ fail, sleep, env = process.env, dryRun = false }) {
  const kubectlBin = resolveExecutable("kubectl");

  function kubectl(cmdArgs, { quiet = false, dryRun: dry = false, input } = {}) {
    if (dry || dryRun) {
      console.log(`[dry-run] kubectl ${cmdArgs.join(" ")}`);
      return { status: 0, stdout: "", stderr: "" };
    }
    const stdio = input
      ? quiet
        ? ["pipe", "pipe", "pipe"]
        : ["pipe", "inherit", "inherit"]
      : quiet
        ? "pipe"
        : "inherit";
    return spawnSync(kubectlBin, cmdArgs, {
      encoding: "utf8",
      stdio,
      shell: false,
      input,
      env,
    });
  }

  function kubectlOut(cmdArgs) {
    const result = kubectl(cmdArgs, { quiet: true });
    return result.status === 0 ? (result.stdout ?? "").trim() : "";
  }

  function requireCluster() {
    if (dryRun) return "dry-run";
    const ctx = kubectlOut(["config", "current-context"]);
    if (!ctx) fail("kubectl has no current context — log in to your OpenShift cluster first");
    return ctx;
  }

  function appsDomain() {
    if (env.REPODY_APPS_DOMAIN?.trim()) return env.REPODY_APPS_DOMAIN.trim();
    if (dryRun) return env.REPODY_INGRESS_DOMAIN?.trim() || "apps.example.com";
    const domain = kubectlOut([
      "get",
      "ingresses.config",
      "cluster",
      "-o",
      "jsonpath={.spec.domain}",
    ]);
    if (domain) return domain;
    const fallback = env.REPODY_INGRESS_DOMAIN?.trim();
    if (fallback) return fallback;
    fail("Could not read cluster apps domain — set REPODY_APPS_DOMAIN or REPODY_INGRESS_DOMAIN");
  }

  function routeHosts(domain, prefix = env.REPODY_ROUTE_PREFIX?.trim() || "repody") {
    return {
      web: `${prefix}-web.${domain}`,
      api: `${prefix}-api.${domain}`,
      auth: `${prefix}-auth.${domain}`,
      files: `${prefix}-files.${domain}`,
      harbor: `${prefix}-harbor.${domain}`,
    };
  }

  function ensureNamespace(name, labels = {}) {
    if (kubectl(["get", "namespace", name], { quiet: true }).status === 0) return;
    const labelArgs = Object.entries(labels).flatMap(([k, v]) => ["--label", `${k}=${v}`]);
    const created = kubectl(["create", "namespace", name, ...labelArgs], { quiet: true });
    if (created.status !== 0) fail(`failed to create namespace ${name}`);
    const deadline = Date.now() + 60_000;
    while (Date.now() < deadline) {
      const phase = kubectlOut(["get", "namespace", name, "-o", "jsonpath={.status.phase}"]);
      if (phase === "Active") return;
      sleep(2000);
    }
    fail(`namespace ${name} did not become Active`);
  }

  function waitForPods(ns, selector, timeoutSec = 300) {
    const result = kubectl(
      [
        "wait",
        "--for=condition=Ready",
        "pod",
        "-l",
        selector,
        "-n",
        ns,
        `--timeout=${timeoutSec}s`,
      ],
      { quiet: true },
    );
    return result.status === 0;
  }

  function stripExternalSecretFinalizers(ns) {
    const names = kubectlOut([
      "get",
      "externalsecret",
      "-n",
      ns,
      "-o",
      "jsonpath={.items[*].metadata.name}",
    ]);
    for (const name of names.split(/\s+/).filter(Boolean)) {
      kubectl(
        [
          "patch",
          "externalsecret",
          name,
          "-n",
          ns,
          "--type=merge",
          "-p",
          '{"metadata":{"finalizers":null}}',
        ],
        { quiet: true },
      );
    }
  }

  function deleteNamespaces(names, { dryRun = false, timeoutSec = 300 } = {}) {
    for (const ns of names) {
      if (!dryRun) stripExternalSecretFinalizers(ns);
      kubectl(["delete", "namespace", ns, "--ignore-not-found", "--wait=false"], { dryRun, quiet: !dryRun });
    }
    if (dryRun) return;
    const deadline = Date.now() + timeoutSec * 1000;
    while (Date.now() < deadline) {
      const remaining = names.filter((name) => kubectl(["get", "namespace", name], { quiet: true }).status === 0);
      if (remaining.length === 0) return;
      for (const name of remaining) {
        stripExternalSecretFinalizers(name);
        kubectl(
          [
            "patch",
            "namespace",
            name,
            "--type=json",
            "-p",
            '[{"op":"replace","path":"/spec/finalizers","value":[]}]',
          ],
          { quiet: true },
        );
      }
      sleep(5000);
    }
    const stuck = names.filter((name) => kubectl(["get", "namespace", name], { quiet: true }).status === 0);
    if (stuck.length) fail(`Namespaces still terminating: ${stuck.join(", ")}`);
  }

  return {
    kubectlBin,
    kubectl,
    kubectlOut,
    requireCluster,
    appsDomain,
    routeHosts,
    ensureNamespace,
    waitForPods,
    stripExternalSecretFinalizers,
    deleteNamespaces,
  };
}
