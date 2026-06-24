export const ARGO_NAMESPACE = "argocd";
export const ARGO_LOCAL_PORT = 8080;
/** Vanilla Argo CD install — standalone, not routed through Repody Gateway. */
export const ARGO_INSTALL_URL =
  "https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml";

/**
 * @param {(cmd: string, args: string[]) => string | null} captureOptional
 */
export function readArgoPortForwardTarget(captureOptional) {
  const insecure = captureOptional?.("kubectl", [
    "-n",
    ARGO_NAMESPACE,
    "get",
    "configmap",
    "argocd-cmd-params-cm",
    "-o",
    "jsonpath={.data.server\\.insecure}",
  ]);
  if (insecure === "true") {
    return { localPort: ARGO_LOCAL_PORT, remotePort: 80, scheme: "http", tlsInsecure: false };
  }
  return { localPort: ARGO_LOCAL_PORT, remotePort: 443, scheme: "https", tlsInsecure: true };
}

/** @param {{ scheme: string; localPort: number }} target */
export function argoLocalBaseUrl(target) {
  const port = target?.localPort ?? ARGO_LOCAL_PORT;
  const scheme = target?.scheme ?? "https";
  return `${scheme}://127.0.0.1:${port}`;
}
