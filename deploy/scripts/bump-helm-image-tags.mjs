import { readFileSync, writeFileSync } from "node:fs";

const IMAGE_KEYS = ["backend", "api", "worker", "web"];

/**
 * @param {string} filePath
 * @returns {string}
 */
export function readHelmImageTag(filePath) {
  const content = readFileSync(filePath, "utf8");
  const match = content.match(
    /^\s{2}api:\s*\r?\n\s{4}tag:\s*["']?([^"'\n#]+)["']?\s*$/m,
  );
  if (!match?.[1]) {
    throw new Error(`Could not read images.api.tag from ${filePath}`);
  }
  return match[1].trim();
}

/**
 * @param {string} filePath
 * @param {string} tag
 */
export function bumpHelmImageTags(filePath, tag) {
  const quoted = `"${tag}"`;
  let content = readFileSync(filePath, "utf8");
  for (const key of IMAGE_KEYS) {
    const pattern = new RegExp(
      `(^\\s{2}${key}:\\s*\\r?\\n\\s{4}tag:\\s*)(["']?)[^"'\n#]+\\2`,
      "m",
    );
    if (!pattern.test(content)) {
      throw new Error(`Could not find images.${key}.tag in ${filePath}`);
    }
    content = content.replace(pattern, `$1${quoted}`);
  }
  writeFileSync(filePath, content, "utf8");
}
