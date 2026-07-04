import { readFileSync } from "node:fs";
import path from "node:path";

/** @param {string} root */
export function readPackageVersion(root) {
  try {
    const pkg = JSON.parse(readFileSync(path.join(root, "package.json"), "utf8"));
    return String(pkg.version ?? "0.1.0");
  } catch {
    return "0.1.0";
  }
}

/** @param {string[]} argv */
export function parseArgs(argv, defaultCmd = "all") {
  const flags = new Set();
  let cmd = defaultCmd;
  for (let i = 2; i < argv.length; i++) {
    const arg = argv[i];
    if (arg.startsWith("--")) flags.add(arg);
    else cmd = arg;
  }
  return { cmd, flags };
}

export function log(section, message) {
  console.log(`\n== ${section} ==\n${message}`);
}

export function fail(message, code = 1) {
  console.error(`\nerror: ${message}\n`);
  process.exit(code);
}

export function sleep(ms) {
  Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, ms);
}
