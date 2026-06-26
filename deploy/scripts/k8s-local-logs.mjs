import { spawn } from "node:child_process";

/** @param {string} pod */
function platformPodLabel(pod) {
  if (pod.startsWith("repody-api-")) return "api";
  if (pod.startsWith("repody-web-")) return "web";
  if (pod.startsWith("repody-worker-ocr-")) return "worker-ocr";
  if (pod.startsWith("repody-worker-fast-")) return "worker-fast";
  if (pod.startsWith("repody-auth-keycloak-") || pod.startsWith("keycloak-")) return "keycloak";
  if (pod.startsWith("repody-hatchet-engine-")) return "hatchet-engine";
  if (pod.startsWith("repody-hatchet-api-")) return "hatchet-api";
  if (pod.startsWith("argocd-server-")) return "argocd";
  if (pod.startsWith("envoy-gateway-")) return "envoy-ctrl";
  if (pod.startsWith("envoy-repody-")) return "envoy";
  return pod.length > 28 ? `${pod.slice(0, 25)}…` : pod;
}

/** App workloads only — skip infra noise (postgres, redis, minio, gateway controller). */
function isAppPlatformPod(pod) {
  if (/postgres|redis|minio|bootstrap|migrations/i.test(pod)) {
    return false;
  }
  return (
    pod.startsWith("repody-api-") ||
    pod.startsWith("repody-web-") ||
    pod.startsWith("repody-worker-") ||
    pod.startsWith("repody-auth-keycloak-") ||
    pod.startsWith("keycloak-") ||
    (pod.startsWith("repody-hatchet-engine-") ||
      pod.startsWith("repody-hatchet-api-"))
  );
}

/** @param {string} line */
function isNoisyLine(line) {
  if (/\/v1\/healthz/.test(line)) return true;
  if (/local-tempo/.test(line)) return true;
  if (/Failed to export span batch/.test(line)) return true;
  if (/Transient error HTTPConnectionPool\(host='local-tempo'/.test(line)) return true;
  if (/\tINFO\t.*status unchanged, bypassing update/.test(line)) return true;
  if (/\tINFO\t.*reconciling gateways/.test(line)) return true;
  if (/\tINFO\t.*open delta watch ID:/.test(line)) return true;
  if (/\tINFO\t.*processing (HTTPRoute|Backend|Gateway)/.test(line)) return true;
  if (/\tINFO\t.*received a status update/.test(line)) return true;
  if (/\tINFO\t.*received an update\s/.test(line)) return true;
  if (/^\{":authority":/.test(line.trim())) return true;
  return false;
}

/**
 * @param {{ capture: (cmd: string, args: string[]) => string, root: string, run?: (cmd: string, args: string[]) => void }} deps
 */
export function createLogCommands({ capture, root, run }) {
  /** @param {string} cmd @param {string[]} args */
  function captureOptional(cmd, args) {
    try {
      return capture(cmd, args);
    } catch {
      return "";
    }
  }

  /** @param {string} namespace */
  function listRunningPods(namespace) {
    try {
      const output = capture("kubectl", [
        "-n",
        namespace,
        "get",
        "pods",
        "--no-headers",
        "-o",
        "custom-columns=NAME:.metadata.name,PHASE:.status.phase",
      ]);
      return output
        .split("\n")
        .map((line) => line.trim())
        .filter(Boolean)
        .map((line) => {
          const [name, phase] = line.split(/\s+/);
          if (!name || phase !== "Running") {
            return null;
          }
          return name;
        })
        .filter(Boolean);
    } catch {
      return [];
    }
  }

  /**
   * @param {string} namespace
   * @param {string} pod
   * @param {string} label
   * @param {boolean} suppressNoise
   */
  function streamPodLogs(namespace, pod, label, suppressNoise) {
    const child = spawn(
      "kubectl",
      ["logs", "-f", "-n", namespace, pod, "--tail=80"],
      { cwd: root, shell: false },
    );

    const prefix = `[${label}] `;
    let buffer = "";

    const flush = (chunk, stream) => {
      buffer += chunk.toString();
      const lines = buffer.split(/\r?\n/);
      buffer = lines.pop() ?? "";
      for (const line of lines) {
        if (!line.trim()) continue;
        if (suppressNoise && isNoisyLine(line)) continue;
        stream.write(`${prefix}${line}\n`);
      }
    };

    child.stdout?.on("data", (chunk) => flush(chunk, process.stdout));
    child.stderr?.on("data", (chunk) => flush(chunk, process.stderr));

    child.on("exit", (code) => {
      if (buffer.trim()) {
        const line = buffer.trim();
        if (!suppressNoise || !isNoisyLine(line)) {
          process.stderr.write(`${prefix}${line}\n`);
        }
      }
      if (code !== 0 && code !== null) {
        console.error(
          `! log stream ended for ${namespace}/${pod} (exit ${code}); other streams continue`,
        );
      }
    });

    return child;
  }

  /**
   * @param {{
   *   minimal?: boolean,
   *   verbose?: boolean,
   *   repodyNamespaces?: string[],
   *   repodyNamespace: string,
   *   envoyNamespace: string,
   *   argoNamespace: string,
   * }} options
   */
  function followPlatformLogs({
    minimal = false,
    verbose = false,
    repodyNamespace,
    repodyNamespaces = repodyNamespace ? [repodyNamespace] : [],
    envoyNamespace,
    argoNamespace,
  }) {
    /** @type {{ ns: string, pod: string, label: string }[]} */
    const streams = [];

    for (const namespace of repodyNamespaces) {
      const repodyPods = listRunningPods(namespace);
      for (const pod of repodyPods) {
        if (!verbose && !isAppPlatformPod(pod)) {
          continue;
        }
        streams.push({
          ns: namespace,
          pod,
          label: platformPodLabel(pod),
        });
      }
    }

    if (verbose) {
      for (const pod of listRunningPods(envoyNamespace)) {
        streams.push({
          ns: envoyNamespace,
          pod,
          label: platformPodLabel(pod),
        });
      }
      if (!minimal) {
        for (const pod of listRunningPods(argoNamespace)) {
          if (pod.startsWith("argocd-server-")) {
            streams.push({
              ns: argoNamespace,
              pod,
              label: platformPodLabel(pod),
            });
          }
        }
      }
    }

    if (streams.length === 0) {
      console.error("No running platform pods to tail yet.");
      process.exit(1);
    }

    console.error(
      verbose
        ? "Verbose logs: all repody pods + gateway + argocd (if full stack)."
        : "App logs: api, web, workers, keycloak, hatchet (health checks & gateway INFO filtered).",
    );
    console.error("Add --logs-all for infra/gateway noise. Ctrl+C to stop.\n");
    for (const { ns, pod, label } of streams) {
      console.error(`  → ${label} (${ns}/${pod})`);
    }
    console.error("");

    /** @type {import("node:child_process").ChildProcess[]} */
    const children = streams.map(({ ns, pod, label }) =>
      streamPodLogs(ns, pod, label, !verbose),
    );

    const shutdown = () => {
      for (const child of children) {
        child.kill("SIGTERM");
      }
      process.exit(0);
    };

    process.on("SIGINT", shutdown);
    process.on("SIGTERM", shutdown);
  }

  return { followPlatformLogs, listRunningPods };
}
