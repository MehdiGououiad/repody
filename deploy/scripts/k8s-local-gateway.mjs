export function createGatewayCommands({
  authHost,
  authNamespace,
  capture,
  captureOptional,
  chartDir,
  envoyChart,
  envoyNamespace,
  envoyVersion,
  heading,
  namespace,
  run,
  waitFor,
}) {
  function envoyGatewayReady() {
    try {
      const phase = capture("kubectl", [
        "-n",
        envoyNamespace,
        "get",
        "pod",
        "-l",
        "app.kubernetes.io/name=gateway-helm",
        "-o",
        "jsonpath={.items[0].status.conditions[?(@.type=='Ready')].status}",
      ]);
      return phase === "True";
    } catch {
      return false;
    }
  }

  function installEnvoyGatewayController() {
    if (envoyGatewayReady()) {
      console.error("ok: Envoy Gateway controller already ready");
      return;
    }
    heading("Installing Envoy Gateway (Gateway API controller)");
    run("helm", [
      "upgrade",
      "--install",
      "eg",
      envoyChart,
      "--version",
      envoyVersion,
      "-n",
      envoyNamespace,
      "--create-namespace",
      "--timeout",
      "10m",
    ]);
    waitFor(
      () => {
        try {
          const phase = capture("kubectl", [
            "-n",
            envoyNamespace,
            "get",
            "pod",
            "-l",
            "app.kubernetes.io/name=gateway-helm",
            "-o",
            "jsonpath={.items[0].status.conditions[?(@.type=='Ready')].status}",
          ]);
          return phase === "True";
        } catch {
          return false;
        }
      },
      "Envoy Gateway controller",
      300_000,
    );
  }

  function gatewayProgrammed() {
    try {
      const listener = capture("kubectl", [
        "-n",
        namespace,
        "get",
        "gateway/repody",
        "-o",
        "jsonpath={.status.listeners[0].conditions[?(@.type=='Programmed')].status}",
      ]);
      return listener === "True";
    } catch {
      return false;
    }
  }

  function gatewayProgress() {
    console.error("\n--- Gateway status ---");
    console.error(captureOptional("kubectl", ["-n", namespace, "get", "gateway,httproute", "-o", "wide"]));
    console.error("\n--- Gateway describe ---");
    console.error(captureOptional("kubectl", ["-n", namespace, "describe", "gateway/repody"]));
    console.error("");
  }

  function envoyGatewayServiceName() {
    return capture("kubectl", [
      "-n",
      envoyNamespace,
      "get",
      "svc",
      "-l",
      "gateway.envoyproxy.io/owning-gateway-name=repody,gateway.envoyproxy.io/owning-gateway-namespace=repody-app",
      "-o",
      "jsonpath={.items[0].metadata.name}",
    ]);
  }

  function resolveKeycloakClusterIp() {
    try {
      return capture("kubectl", [
        "-n",
        authNamespace,
        "get",
        "svc/keycloak",
        "-o",
        "jsonpath={.spec.clusterIP}",
      ]);
    } catch {
      return "";
    }
  }

  function currentAuthHostAliasIp() {
    try {
      return capture("helm", [
        "get",
        "values",
        "repody",
        "-n",
        namespace,
        "-o",
        "jsonpath={.gatewayApi.authHostAliasIp}",
      ]);
    } catch {
      return "";
    }
  }

  /** Helm --set fragments when Keycloak ClusterIP is already known. */
  function authHostAliasHelmSets() {
    const keycloakIp = resolveKeycloakClusterIp();
    if (!keycloakIp) return [];
    return ["--set", `gatewayApi.authHostAliasIp=${keycloakIp}`];
  }

  function ensureWebAuthHostAlias() {
    const keycloakIp = resolveKeycloakClusterIp();
    if (!keycloakIp) return;
    const current = currentAuthHostAliasIp();
    if (current === keycloakIp) {
      console.error(`ok: web hostAlias already ${keycloakIp} -> ${authHost}`);
      return;
    }
    console.error(`web hostAlias ${keycloakIp} -> ${authHost} (was: ${current || "unset"})`);
    run("helm", [
      "upgrade",
      "repody",
      chartDir,
      "-n",
      namespace,
      "--reuse-values",
      "--set",
      `gatewayApi.authHostAliasIp=${keycloakIp}`,
      "--timeout",
      "10m",
    ]);
    run("kubectl", [
      "-n",
      namespace,
      "rollout",
      "restart",
      "deployment",
      "-l",
      "app.kubernetes.io/component=edge",
    ]);
  }

  function ensureEnvoyNodePort() {
    if (!envoyGatewayServiceName()) return;
    const svc = envoyGatewayServiceName();
    const nodePort = capture("kubectl", [
      "-n",
      envoyNamespace,
      "get",
      `svc/${svc}`,
      "-o",
      "jsonpath={.spec.ports[0].nodePort}",
    ]);
    if (nodePort === "30080") {
      console.error("ok: Envoy Gateway NodePort 30080");
      return;
    }
    console.error(`patch ${svc} to NodePort 30080`);
    run("kubectl", [
      "patch",
      "svc",
      svc,
      "-n",
      envoyNamespace,
      "--type=json",
      "-p",
      '[{"op":"replace","path":"/spec/type","value":"NodePort"},{"op":"replace","path":"/spec/ports/0/nodePort","value":30080}]',
    ]);
  }

  return {
    authHostAliasHelmSets,
    ensureEnvoyNodePort,
    ensureWebAuthHostAlias,
    gatewayProgrammed,
    gatewayProgress,
    installEnvoyGatewayController,
    resolveKeycloakClusterIp,
  };
}
