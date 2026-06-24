import { spawnSync } from "node:child_process";

/**
 * @param {string} root
 * @param {number} [length]
 */
export function gitShortSha(root, length = 12) {
  const result = spawnSync("git", ["rev-parse", `--short=${length}`, "HEAD"], {
    cwd: root,
    encoding: "utf8",
    shell: process.platform === "win32",
  });
  if (result.status === 0) {
    const sha = result.stdout.trim();
    if (sha) return sha;
  }
  throw new Error("Could not resolve git HEAD — run from a git checkout");
}

/**
 * @param {string} root
 */
export function gitHeadRevision(root) {
  const result = spawnSync("git", ["rev-parse", "HEAD"], {
    cwd: root,
    encoding: "utf8",
    shell: process.platform === "win32",
  });
  if (result.status !== 0 || !result.stdout.trim()) {
    throw new Error("Could not resolve git HEAD — run from a git checkout");
  }
  return result.stdout.trim();
}
