import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import path from "node:path";

/**
 * Shared Vault + External Secrets helpers for vendor lab scripts.
 * Production clients follow the same contract — see docs/deploy/SECRETS.md
 *
 * @param {object} opts
 * @param {string} opts.root
 * @param {(args: string[], options?: object) => object} opts.kubectl
 * @param {(args: string[]) => string} opts.kubectlOut
 * @param {(message: string, code?: number) => never} opts.fail
 * @param {(ms: number) => void} opts.sleep
 * @param {string} opts.repodyNamespace
 * @param {string} opts.vaultNamespace
 * @param {string} opts.runtimeDir
 * @param {string} [opts.secretStoreName]
 */
export function createVaultEsoHelpers({
  root,
  kubectl,
  kubectlOut,
  fail,
  sleep,
  repodyNamespace,
  vaultNamespace,
  runtimeDir,
  secretStoreName = "vault-repody",
}) {
  function patchEsYaml(relativePath) {
    const raw = readFileSync(path.join(root, relativePath), "utf8");
    return raw.replaceAll("CHANGE_ME_SECRET_STORE", secretStoreName);
  }

  function putVaultKv(mountPath, kv) {
    const script = `cat > /tmp/payload.json <<'EOFPAYLOAD'
${JSON.stringify(kv, null, 0)}
EOFPAYLOAD
vault kv put ${mountPath} @/tmp/payload.json`;
    const result = kubectl(["exec", "-n", vaultNamespace, "vault-0", "--", "sh", "-c", script], { quiet: true });
    if (result.status !== 0) fail(`vault kv put ${mountPath} failed`);
  }

  /**
   * @param {string[]} externalSecretFiles relative paths under repo root
   * @param {string} [manifestName]
   */
  function applyExternalSecrets(externalSecretFiles, manifestName = "externalsecrets.yaml") {
    const manifest = externalSecretFiles.map(patchEsYaml).join("\n---\n");
    const manifestPath = path.join(runtimeDir, manifestName);
    mkdirSync(runtimeDir, { recursive: true });
    writeFileSync(manifestPath, manifest, "utf8");
    kubectl(["apply", "-f", manifestPath], { quiet: true });
    return manifestPath;
  }

  function waitExternalSecrets(timeoutSec = 300) {
    const deadline = Date.now() + timeoutSec * 1000;
    while (Date.now() < deadline) {
      const pending = kubectlOut([
        "get",
        "externalsecret",
        "-n",
        repodyNamespace,
        "-o",
        'jsonpath={range .items[*]}{.status.conditions[?(@.type=="Ready")].status}{"\\n"}{end}',
      ]);
      const lines = pending.split("\n").filter(Boolean);
      if (lines.length > 0 && lines.every((s) => s === "True")) return;
      sleep(5000);
    }
    fail("ExternalSecrets did not become Ready");
  }

  /** Bundled lab ExternalSecret set (registry + data plane + runtime). */
  const bundledExternalSecretFiles = [
    "deploy/client/secrets/registry-pull.externalsecret.example.yaml",
    "deploy/client/secrets/data-plane.externalsecret.example.yaml",
    "deploy/client/secrets/runtime-bundled.externalsecret.example.yaml",
  ];

  return {
    patchEsYaml,
    putVaultKv,
    applyExternalSecrets,
    waitExternalSecrets,
    bundledExternalSecretFiles,
  };
}

/** @param {string} registryHost e.g. harbor.example.com/repody or 127.0.0.1:30500/repody */
export function dockerConfigJson(registryHost, username, password) {
  const auth = Buffer.from(`${username}:${password}`).toString("base64");
  return JSON.stringify({
    auths: {
      [registryHost]: { username, password, auth },
    },
  });
}
