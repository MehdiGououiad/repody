import dns from "node:dns";

/**
 * OpenShift Routes for lab infra UIs (Argo CD, Vault, Harbor on host).
 * Repody app/auth routes come from Helm when global.openshift.routes.enabled=true.
 */

export function createLabUiRoutes({ kubectl, kubectlOut, fail, log, dryRun }) {
  function routeHosts(domain, prefix = process.env.REPODY_ROUTE_PREFIX?.trim() || "repody") {
    return {
      web: `${prefix}-web.${domain}`,
      api: `${prefix}-api.${domain}`,
      auth: `${prefix}-auth.${domain}`,
      files: `${prefix}-files.${domain}`,
      argocd: `${prefix}-argocd.${domain}`,
      vault: `${prefix}-vault.${domain}`,
      harbor: `${prefix}-harbor.${domain}`,
    };
  }

  function resolveHostGatewayIp() {
    const fromEnv = process.env.REPODY_CRC_HOST_GATEWAY?.trim();
    if (fromEnv) return fromEnv;

    for (const [resource, ns] of [
      ["deployment/repody-api", "repody"],
      ["statefulset/vault", "vault"],
    ]) {
      if (kubectlOut(["get", resource, "-n", ns, "-o", "name"]).length === 0) continue;
      const ip = kubectlOut([
        "exec",
        resource,
        "-n",
        ns,
        "--",
        "sh",
        "-c",
        "getent hosts host.crc.testing | awk '{print $1; exit}'",
      ]);
      if (ip && /^\d+\.\d+\.\d+\.\d+$/.test(ip)) return ip;
    }

    try {
      const ip = dns.lookupSync("host.crc.testing");
      if (ip && ip !== "127.0.0.1") return ip;
    } catch {
      /* fall through */
    }

    fail(
      "Could not resolve host.crc.testing for Harbor UI route — set REPODY_CRC_HOST_GATEWAY to the CRC host gateway IP",
    );
  }

  function applyRoute(manifest) {
    const result = kubectl(["apply", "-f", "-"], { dryRun, input: manifest });
    if (result.status !== 0) fail("OpenShift UI route apply failed");
  }

  function applyInfraRoutes(domain, { harbor = true } = {}) {
    const hosts = routeHosts(domain);
    const harborPort = Number(process.env.REPODY_HARBOR_PORT?.trim() || "5080");

    applyRoute(`apiVersion: route.openshift.io/v1
kind: Route
metadata:
  name: argocd-server
  namespace: argocd
  labels:
    app.kubernetes.io/part-of: repody-lab
spec:
  host: ${hosts.argocd}
  to:
    kind: Service
    name: argocd-server
    weight: 100
  port:
    targetPort: https
  tls:
    termination: passthrough
    insecureEdgeTerminationPolicy: Redirect
`);

    applyRoute(`apiVersion: route.openshift.io/v1
kind: Route
metadata:
  name: vault-ui
  namespace: vault
  labels:
    app.kubernetes.io/part-of: repody-lab
spec:
  host: ${hosts.vault}
  to:
    kind: Service
    name: vault
    weight: 100
  port:
    targetPort: 8200
  tls:
    termination: edge
    insecureEdgeTerminationPolicy: Redirect
`);

    if (harbor) {
      const gatewayIp = dryRun ? "127.0.0.1" : resolveHostGatewayIp();
      applyRoute(`apiVersion: v1
kind: Service
metadata:
  name: harbor-external
  namespace: repody
  labels:
    app.kubernetes.io/part-of: repody-lab
spec:
  ports:
    - name: http
      port: 80
      targetPort: ${harborPort}
---
apiVersion: v1
kind: Endpoints
metadata:
  name: harbor-external
  namespace: repody
  labels:
    app.kubernetes.io/part-of: repody-lab
subsets:
  - addresses:
      - ip: ${gatewayIp}
    ports:
      - name: http
        port: ${harborPort}
---
apiVersion: route.openshift.io/v1
kind: Route
metadata:
  name: harbor-ui
  namespace: repody
  labels:
    app.kubernetes.io/part-of: repody-lab
spec:
  host: ${hosts.harbor}
  to:
    kind: Service
    name: harbor-external
    weight: 100
  port:
    targetPort: http
  tls:
    termination: edge
    insecureEdgeTerminationPolicy: Allow
`);
    }

    log(
      "routes",
      [
        "lab UI routes (OpenShift — no port-forward):",
        `  Argo CD:  https://${hosts.argocd}`,
        `  Vault:    https://${hosts.vault}  (token: root, lab only)`,
        harbor ? `  Harbor:   https://${hosts.harbor}  (admin / see lab README)` : "  Harbor:   http://localhost:5080 (host Compose)",
        `  Repody:   https://${hosts.web}  (after GitOps sync)`,
        `  API:      https://${hosts.api}/v1/healthz/live`,
        `  Auth:     https://${hosts.auth}`,
        `  Files:    https://${hosts.files}`,
      ].join("\n"),
    );

    return hosts;
  }

  return { routeHosts, applyInfraRoutes };
}
