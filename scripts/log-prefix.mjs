#!/usr/bin/env node
/**
 * Prefix each line from a child process stdout/stderr (for multiplexed platform logs).
 */
import { spawn } from "node:child_process";

/**
 * @param {string} label
 * @param {string} command
 * @param {string[]} args
 * @param {import("node:child_process").SpawnOptions} [options]
 */
export function spawnPrefixed(label, command, args, options = {}) {
  const child = spawn(command, args, {
    stdio: ["ignore", "pipe", "pipe"],
    ...options,
  });

  /** @param {import("node:stream").Readable | null} stream @param {boolean} isErr */
  function pipe(stream, isErr) {
    if (!stream) return;
    let buffer = "";
    stream.setEncoding("utf8");
    stream.on("data", (chunk) => {
      buffer += chunk;
      const lines = buffer.split(/\r?\n/);
      buffer = lines.pop() ?? "";
      for (const line of lines) {
        if (!line) continue;
        const out = `[${label}] ${line}\n`;
        if (isErr) process.stderr.write(out);
        else process.stdout.write(out);
      }
    });
    stream.on("end", () => {
      if (buffer.trim()) {
        const out = `[${label}] ${buffer}\n`;
        if (isErr) process.stderr.write(out);
        else process.stdout.write(out);
      }
    });
  }

  pipe(child.stdout, false);
  pipe(child.stderr, true);
  return child;
}
