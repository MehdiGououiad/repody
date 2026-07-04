/**
 * Vault + Kubernetes auth bootstrap for vendor lab scripts.
 * @see https://developer.hashicorp.com/vault/docs/auth/kubernetes
 */

/**
 * @param {object} opts
 * @param {(args: string[], options?: object) => object} opts.exec cluster CLI exec (kubectl/oc)
 * @param {(args: string[]) => string} opts.getOut
 * @param {(message: string, code?: number) => never} opts.fail
 * @param {(ms: number) => void} opts.sleep
 * @param {string} opts.vaultNamespace
 */
export function createVaultBootstrap({ exec, getOut, fail, sleep, vaultNamespace }) {
  function vaultExec(vaultArgs) {
    return exec(["exec", "-n", vaultNamespace, "vault-0", "--", "vault", ...vaultArgs], { quiet: true });
  }

  function applyVaultAuthTokenSecret() {
    const manifest = `apiVersion: v1
kind: Secret
metadata:
  name: vault-auth-token
  namespace: ${vaultNamespace}
  annotations:
    kubernetes.io/service-account.name: vault-auth
type: kubernetes.io/service-account-token
`;
    exec(["apply", "-f", "-"], { input: manifest, quiet: true });
    const deadline = Date.now() + 120_000;
    while (Date.now() < deadline) {
      const token = getOut([
        "get",
        "secret",
        "vault-auth-token",
        "-n",
        vaultNamespace,
        "-o",
        "jsonpath={.data.token}",
      ]);
      if (token) return;
      sleep(2000);
    }
    fail("vault-auth-token secret was not populated");
  }

  function configureVault() {
    const policy = `path "secret/data/repody/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}
path "secret/metadata/repody/*" {
  capabilities = ["list", "read", "delete"]
}
`;
    const enableKv = vaultExec(["secrets", "enable", "-path=secret", "kv-v2"]);
    if (enableKv.status !== 0 && !(enableKv.stderr ?? "").includes("path is already in use")) {
      fail("vault secrets enable failed");
    }
    exec(
      ["exec", "-n", vaultNamespace, "vault-0", "--", "sh", "-c", `vault policy write repody - <<'EOF'\n${policy}\nEOF`],
      { quiet: true },
    );
    const enableAuth = vaultExec(["auth", "enable", "kubernetes"]);
    if (enableAuth.status !== 0 && !(enableAuth.stderr ?? "").includes("path is already in use")) {
      fail("vault kubernetes auth enable failed");
    }
    const reviewer = getOut([
      "get",
      "secret",
      "vault-auth-token",
      "-n",
      vaultNamespace,
      "-o",
      "jsonpath={.data.token}",
    ]);
    const reviewerJwt = Buffer.from(reviewer, "base64").toString("utf8");
    vaultExec([
      "write",
      "auth/kubernetes/config",
      `token_reviewer_jwt=${reviewerJwt}`,
      "kubernetes_host=https://kubernetes.default.svc:443",
      "kubernetes_ca_cert=@/var/run/secrets/kubernetes.io/serviceaccount/ca.crt",
    ]);
    vaultExec([
      "write",
      "auth/kubernetes/role/repody",
      "bound_service_account_names=external-secrets",
      "bound_service_account_namespaces=external-secrets",
      "policies=repody",
      "ttl=24h",
    ]);
  }

  return { vaultExec, applyVaultAuthTokenSecret, configureVault };
}
