export function createArgoCommands({
  applyJson,
  argoInstallUrl,
  argoLocalRootApp,
  argoNamespace,
  argoRepoUrl,
  capture,
  captureOptional,
  captureWithInput,
  ensureNamespace,
  heading,
  run,
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

  function resetGatewayEraArgoPatches() {
    const raw = captureOptional("kubectl", [
      "-n",
      argoNamespace,
      "get",
      "configmap",
      "argocd-cmd-params-cm",
      "-o",
      "json",
    ]);
    if (!raw) return;
    try {
      const cm = JSON.parse(raw);
      const data = { ...(cm.data ?? {}) };
      let changed = false;
      for (const key of ["server.insecure", "server.grpc.web"]) {
        if (key in data) {
          delete data[key];
          changed = true;
        }
      }
      if (!changed) return;
      applyJson({
        apiVersion: "v1",
        kind: "ConfigMap",
        metadata: { name: "argocd-cmd-params-cm", namespace: argoNamespace },
        data,
      });
      run("kubectl", ["-n", argoNamespace, "rollout", "restart", "deploy/argocd-server"]);
      waitForArgoServer("Argo CD server after standalone reset", 300_000);
      console.error("ok: removed Gateway-era Argo server flags (insecure / grpc.web)");
    } catch {
      // non-fatal
    }
  }

  function installArgoCd() {
    if (argoCdReady()) {
      console.error("ok: Argo CD server already ready");
      resetGatewayEraArgoPatches();
      return;
    }
    heading("Installing Argo CD (upstream manifest, standalone)");
    console.error(
      "  Optional for local GitOps. Fast path without Argo: pnpm dev  (--minimal)",
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
    resetGatewayEraArgoPatches();
    console.error("ok: Argo CD installed — run: pnpm argocd:port-forward");
  }

  function registerLocalGitOpsRootApp() {
    run("kubectl", ["apply", "-f", argoLocalRootApp]);
    console.error("ok: repody-local-root Application registered (Repody GitOps only)");
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
        "No local GitHub credential found for Argo CD; private repo sync may need a repository secret.",
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

  return {
    configureArgoRepositoryCredentials,
    installArgoCd,
    registerLocalGitOpsRootApp,
  };
}
