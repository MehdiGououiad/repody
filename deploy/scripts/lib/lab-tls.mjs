import { existsSync, mkdirSync } from "node:fs";
import path from "node:path";
import { resolveExecutable } from "../runtime-env.mjs";

/**
 * @param {(cmd: string, args: string[], opts?: object) => object} run
 */
export function resolveOpenSsl(run) {
  const candidates = ["openssl"];
  if (process.platform === "win32") {
    const gitSsl = path.join(process.env["ProgramFiles"] ?? "C:\\Program Files", "Git", "usr", "bin", "openssl.exe");
    if (existsSync(gitSsl)) candidates.unshift(gitSsl);
  }
  for (const candidate of candidates) {
    const bin = candidate.includes(path.sep) ? candidate : resolveExecutable(candidate);
    if (run(bin, ["version"], { quiet: true }).status === 0) return bin;
  }
  return null;
}

/**
 * @param {object} opts
 * @param {(args: string[], options?: object) => object} opts.apply cluster apply (kubectl/oc apply)
 * @param {(cmd: string, args: string[], opts?: object) => object} opts.run shell run for openssl
 * @param {string} opts.runtimeDir
 * @param {string} opts.domain
 * @param {string[]} opts.sanHosts
 * @param {string} opts.namespace
 * @param {(message: string, code?: number) => never} opts.fail
 */
export function createTlsSecret({ apply, run, runtimeDir, domain, sanHosts, namespace, fail }) {
  const certDir = path.join(runtimeDir, "tls");
  mkdirSync(certDir, { recursive: true });
  const keyPath = path.join(certDir, "tls.key");
  const certPath = path.join(certDir, "tls.crt");
  const openssl = resolveOpenSsl(run);
  if (!openssl) fail("openssl TLS generation failed — install OpenSSL or Git for Windows");
  const san = [domain, ...sanHosts.filter((h) => h !== domain)];
  const gen = run(
    openssl,
    [
      "req",
      "-x509",
      "-nodes",
      "-days",
      "365",
      "-newkey",
      "rsa:2048",
      "-keyout",
      keyPath,
      "-out",
      certPath,
      "-subj",
      `/CN=${domain}`,
      "-addext",
      `subjectAltName=${san.map((h) => `DNS:${h}`).join(",")}`,
    ],
    { quiet: true },
  );
  if (gen.status !== 0) fail(`openssl TLS generation failed: ${gen.stderr ?? ""}`);
  apply(["delete", "secret", "repody-tls", "-n", namespace, "--ignore-not-found"], { quiet: true });
  apply(["create", "secret", "tls", "repody-tls", "-n", namespace, `--cert=${certPath}`, `--key=${keyPath}`], {
    quiet: true,
  });
}
