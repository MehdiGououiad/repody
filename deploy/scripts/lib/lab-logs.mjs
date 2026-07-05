/**
 * Verify Repody pods emit structured JSON logs (AUDIT_LOG_JSON=true).
 * @see https://kubernetes.io/docs/concepts/cluster-administration/logging/
 */

/**
 * @param {(args: string[]) => string} kubectlOut
 * @param {(message: string, code?: number) => never} fail
 * @param {string} namespace
 */
export function verifyJsonLogs({ kubectlOut, fail, namespace = "repody" }) {
  const targets = [
    { kind: "deploy", name: "repody-api", label: "API" },
    { kind: "deploy", name: "repody-web", label: "Web" },
  ];
  const issues = [];

  for (const { kind, name, label } of targets) {
    const ready = kubectlOut([
      "get",
      kind,
      name,
      "-n",
      namespace,
      "-o",
      "jsonpath={.status.readyReplicas}",
    ]);
    if (ready !== "1") {
      issues.push(`${label}: deployment not ready (${ready || "0"} replicas)`);
      continue;
    }

    const raw = kubectlOut(["logs", `${kind}/${name}`, "-n", namespace, "--tail=20", "--since=10m"]);
    const lines = raw.split("\n").map((l) => l.trim()).filter(Boolean);
    if (lines.length === 0) {
      issues.push(`${label}: no log lines in last 10m`);
      continue;
    }

    let jsonLines = 0;
    for (const line of lines.slice(-8)) {
      if (line.startsWith("{") && line.endsWith("}")) {
        try {
          JSON.parse(line);
          jsonLines++;
        } catch {
          /* non-json line */
        }
      }
    }
    if (jsonLines === 0) {
      issues.push(`${label}: no JSON log lines (expected AUDIT_LOG_JSON=true)`);
    }
  }

  if (issues.length) {
    fail(`Log verification failed:\n  - ${issues.join("\n  - ")}`);
  }

  return { ok: true, checked: targets.length };
}
