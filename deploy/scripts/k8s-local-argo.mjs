export function createArgoCommands({
  applyJson,
  argoInstallUrl,
  argoNamespace,
  argoRepoUrl,
  capture,
  captureOptional,
  captureWithInput,
  ensureNamespace,
  heading,
  run,
  runNoShell,
  waitFor,
  waitForWithProgress,
}) {
  function argoServerReadyReplicas() {
    try {
      const ready = capture("kubectl", [
        "-n",
        argoNamespace,
        "get",
        "deploy/argocd-server",
        "-o",
        "jsonpath={.status.readyReplicas}",
      ]);
      return Number(ready) >= 1;
    } catch {
      return false;
    }
  }

  function argoCdReady() {
    return argoServerReadyReplicas();
  }

  function argoCdProgress() {
    const pods = captureOptional("kubectl", [
      "-n",
      argoNamespace,
      "get",
      "pods",
      "-l",
      "app.kubernetes.io/name=argocd-server",
      "--no-headers",
    ]);
    if (pods && !pods.startsWith("error")) {
      console.error(`  argocd-server: ${pods.split(/\r?\n/)[0]}`);
      return;
    }
    const all = captureOptional("kubectl", [
      "-n",
      argoNamespace,
      "get",
      "pods",
      "--no-headers",
    ]);
    if (all && !all.startsWith("error")) {
      const notReady = all
        .split(/\r?\n/)
        .filter((line) => line && !/\s1\/1\s|\s2\/2\s|\s3\/3\s/.test(line));
      if (notReady.length) {
        console.error(`  argocd not ready: ${notReady.slice(0, 3).join(" | ")}`);
      }
    }
  }

  function waitForArgoServer(label, timeoutMs) {
    const waiter = waitForWithProgress ?? waitFor;
    if (waiter.length >= 4) {
      waiter(() => argoServerReadyReplicas(), label, timeoutMs, 5_000, argoCdProgress, 30_000);
      return;
    }
    waitFor(() => argoServerReadyReplicas(), label, timeoutMs);
  }

  function installArgoCd() {
    if (argoCdReady()) {
      console.error("ok: Argo CD server already ready");
      configureLocalArgoGateway();
      return;
    }
    heading("Installing Argo CD");
    console.error(
      "  First install can take 5–10 min (image pulls). For faster dev, use: pnpm k8s:local -- --minimal",
    );
    ensureNamespace(argoNamespace);
    run("kubectl", [
      "apply",
      "-n",
      argoNamespace,
      "--server-side",
      "--force-conflicts",
      "-f",
      argoInstallUrl,
    ]);
    waitForArgoServer("Argo CD server", 600_000);
    configureLocalArgoGateway();
  }

  function configureLocalArgoGateway() {
    if (!argoCdReady()) {
      return;
    }
    try {
      const insecure = capture("kubectl", [
        "-n",
        argoNamespace,
        "get",
        "configmap",
        "argocd-cmd-params-cm",
        "-o",
        "jsonpath={.data.server\\.insecure}",
      ]);
      if (insecure === "true") {
        console.error("ok: Argo CD already configured for Gateway HTTP");
        configureArgoResourceExclusions();
        return;
      }
    } catch {
      // patch below
    }
    runNoShell("kubectl", [
      "-n",
      argoNamespace,
      "patch",
      "configmap",
      "argocd-cmd-params-cm",
      "--type=merge",
      "-p",
      '{"data":{"server.insecure":"true"}}',
    ]);
    configureArgoResourceExclusions();
    run("kubectl", ["-n", argoNamespace, "rollout", "restart", "deploy/argocd-server"]);
    waitForArgoServer("Argo CD server ready for Gateway HTTP", 300_000);
  }

  function configureArgoResourceExclusions() {
    const exclusionsYaml = `- apiGroups:
  - batch
  kinds:
  - Job
  clusters:
  - "*"
`;
    runNoShell("kubectl", [
      "-n",
      argoNamespace,
      "patch",
      "configmap",
      "argocd-cm",
      "--type=merge",
      "-p",
      JSON.stringify({
        data: {
          "resource.exclusions": exclusionsYaml,
        },
      }),
    ]);
  }

  function readGitHubCredential() {
    try {
      const output = captureWithInput(
        "git",
        ["credential", "fill"],
        "protocol=https\nhost=github.com\npath=MehdiGououiad/repody.git\n\n",
      );
      const values = new Map(
        output
          .split(/\r?\n/)
          .filter(Boolean)
          .map((line) => {
            const index = line.indexOf("=");
            return [line.slice(0, index), line.slice(index + 1)];
          }),
      );
      const username = values.get("username");
      const password = values.get("password");
      if (!username || !password) {
        return null;
      }
      return { username, password };
    } catch {
      return null;
    }
  }

  function configureArgoRepositoryCredentials() {
    const credential = readGitHubCredential();
    if (!credential) {
      console.error(
        "No local GitHub credential found for Argo CD; private repo comparison may require adding a repository secret.",
      );
      return;
    }

    applyJson({
      apiVersion: "v1",
      kind: "Secret",
      metadata: {
        name: "repody-github-repository",
        namespace: argoNamespace,
        labels: {
          "argocd.argoproj.io/secret-type": "repository",
        },
      },
      stringData: {
        type: "git",
        url: argoRepoUrl,
        username: credential.username,
        password: credential.password,
      },
    });
  }

  return { configureArgoRepositoryCredentials, installArgoCd };
}
